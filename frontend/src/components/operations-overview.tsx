"use client";

import { ArrowRightIcon, HardDrivesIcon } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState } from "react";
import { beijingTime, labels, type SnapshotState } from "@/lib/data-center-api";
import { OperationsDeviceCategories } from "./operations-device-categories";

export function OperationsOverview({ state }: { state: SnapshotState }) {
  const id = useId();
  const [now, setNow] = useState(() => new Date());
  const [selectedKind, setSelectedKind] = useState<string | null>(null);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const categoryTrigger = useRef<HTMLElement | null>(null);

  function selectKind(kind: string) {
    categoryTrigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setSelectedKind(kind);
  }
  function closeDevices() {
    setSelectedKind(null);
    categoryTrigger.current?.focus();
  }

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (selectedKind !== null) { detailHeading.current?.scrollIntoView({ block: "start" }); detailHeading.current?.focus({ preventScroll: true }); }
  }, [selectedKind]);

  const data = state?.data;
  const failure = state.error;
  const stale = !!data && (!!failure || state?.stale || !state?.fetched_at || now.getTime() - Date.parse(state.fetched_at) > 30000);
  const metrics = data ? [["处方总数", data.summary.total_prescriptions], ["排队中", data.summary.batch_counts.queued], ["进行中", data.summary.batch_counts.running], ["已暂停", data.summary.batch_counts.paused], ["已完成", data.summary.batch_counts.completed], ["已取消", data.summary.batch_counts.cancelled], ["已配发袋数", data.summary.dispatched_bags], ["活跃报警", data.summary.active_alarms], ["袋 / 运行小时", data.summary.bags_per_virtual_hour]] : [];
  const selected = data?.devices.filter(device => selectedKind === "" || device.kind === selectedKind) ?? [];
  const selectedName = selectedKind === "" ? "全部设备" : data?.devices.find(device => device.kind === selectedKind)?.kind_name ?? "设备";

  return <div className="ops-content">
    <section className="ops-platform-head" aria-label="仿真平台状态">
      <div><h3>中药煎药流程仿真平台</h3><p>流程仿真总览 · 只读</p></div>
      <div className="ops-status-row"><span className="ops-tag">{data ? `${stale ? "上次状态：" : ""}${data.clock.running ? "真实计时运行" : "已暂停"}` : "尚无运行数据"}</span>{data && <span className="ops-tag">真实时间 · {data.clock.speed} 倍速</span>}<span className={"ops-tag" + (failure || stale ? " ops-tag-warning" : "")} role="status">{failure ? "更新失败" : stale ? "数据已过期" : state?.refreshing ? "后台更新中" : data ? "数据已同步" : "正在连接"}</span><time dateTime={now.toISOString()} aria-label="当前北京时间">{new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" }).format(now)}</time></div>
    </section>
    <div className="ops-sync"><p>数据读取时间：{beijingTime(state.fetched_at)} · 使用上方刷新按钮更新总览</p></div>
    {failure && <p className="ops-feedback ops-feedback-error" role="alert">{failure}{data ? " 当前保留上次成功读取的数据。" : " 暂无可显示的运行数据。"}</p>}
    {stale && !failure && <p className="ops-feedback" role="status">当前显示上次快照，后台正在尝试更新；运行状态和指标请以数据读取时间为准。</p>}
    {!data && !failure && <p className="ops-empty" role="status">正在连接仿真平台并读取总览…</p>}
    {data && <>
      <section className="ops-clock" aria-label="全局仿真状态"><div><h3>全局仿真状态</h3><p>按现实时间计时：1 秒就是现实 1 秒，调剂 10 分钟需实际运行 10 分钟。</p></div><p className="ops-clock-note">{data.clock.running ? "平台正在按真实时间运行。暂停期间不累计工序用时，继续后从原进度运行。" : "平台已暂停，当前设备分配与工序进度保留。"} 全局控制请在仿真平台操作。</p></section>
      {Object.values(data.summary.batch_counts).every(count => count === 0) && <p className="ops-feedback">当前没有仿真批次。可在仿真平台录入处方或生成演示数据后查看运行情况。</p>}
      <section aria-labelledby={`${id}-metrics`}><div className="ops-section-head"><h3 id={`${id}-metrics`}>总体指标 · 真实计时</h3><p>利用率与吞吐量为仿真统计，非实际工厂性能承诺</p></div><dl className="ops-metrics">{metrics.map(([label, value]) => <div key={label}><dt>{label}</dt><dd className={label === "已完成" ? "ops-success" : label === "活跃报警" && Number(value) > 0 ? "ops-danger" : undefined}>{value}</dd></div>)}</dl></section>
      <section aria-labelledby={`${id}-batches`}><div className="ops-section-head"><h3 id={`${id}-batches`}>批次状态分布</h3></div><dl className="ops-counts"><div><dt>等待资源</dt><dd>{data.summary.waiting_batches} 批</dd></div>{Object.entries(data.summary.batch_counts).map(([status, value]) => <div key={status}><dt>{labels[status]}</dt><dd>{value} 批</dd></div>)}</dl></section>
      <section aria-labelledby={`${id}-devices`}><div className="ops-section-head"><h3 id={`${id}-devices`}>设备分类 <small>共 {data.devices.length} 台</small></h3><button className="ops-text-button" onClick={() => selectKind("")}>查看全部设备 <ArrowRightIcon size={16} aria-hidden="true" /></button></div><OperationsDeviceCategories devices={data.devices} onSelect={selectKind} /></section>
      {selectedKind !== null && <section className="ops-device-detail" aria-labelledby={`${id}-detail`}><div className="ops-section-head"><h3 id={`${id}-detail`} tabIndex={-1} ref={detailHeading}><HardDrivesIcon size={20} aria-hidden="true" />{selectedName} · 状态与累计利用率</h3><button className="ops-text-button" onClick={closeDevices}>收起设备列表</button></div><p>累计利用率为设备加入后累计有效工作时间占比，不等同于今日利用率。</p><div className="ops-table-scroll" tabIndex={0} role="region" aria-label="运行总览设备列表"><table><thead><tr><th scope="col">设备编号</th><th scope="col">设备名称</th><th scope="col">状态</th><th scope="col">关联批次</th><th scope="col">累计利用率</th></tr></thead><tbody>{selected.map(device => <tr key={device.id}><td>{device.id}</td><td>{device.name}</td><td>{labels[device.status] ?? device.status}</td><td>{device.batch_id ?? "—"}</td><td>{device.utilization_percent}%</td></tr>)}</tbody></table>{!selected.length && <p className="ops-empty">该分类暂无设备</p>}</div></section>}
    </>}
    <p className="ops-footnote">仿真演示数据，不用于临床煎药或真实设备控制。</p>
  </div>;
}
