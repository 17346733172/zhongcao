"use client";

import { ArrowsClockwiseIcon, FileTextIcon, StopIcon } from "@phosphor-icons/react";
import { beijingTime, labels } from "@/lib/data-center-api";
import type { DataCenterSnapshotReader } from "@/lib/use-data-center-snapshot";

const groups = {
  pots: { number: "01", title: "使用中的药锅", name: "药锅", description: "自动同步使用中的煎药锅及关联批次" },
  other: { number: "02", title: "使用中的其他设备", name: "非煎药锅设备", description: "自动同步除煎药锅外所有使用中的设备及关联批次" },
} as const;

export function ActiveDevicesTask({ snapshotReader, group }: { snapshotReader: DataCenterSnapshotReader; group: keyof typeof groups }) {
  const { state, busy, slowConnection, refreshData } = snapshotReader;
  const { data, fetched_at, stale, error, refreshing } = state;
  const { number, title, name, description } = groups[group];
  const devices = data?.devices.filter(device => device.status === "busy" && (group === "pots" ? device.kind === "pot" : device.kind !== "pot")) ?? [];
  const outdated = stale || !!error;
  const headingId = `te-active-devices-${number}`;

  return <article className="te-task-card te-active-devices" aria-labelledby={headingId}>
    <div className="te-task-heading">
      <div className="te-task-context">
        <div className="te-task-title"><h3 id={headingId}>任务区域 {number}</h3><span className="te-status">{title}</span>{data && <span className="te-batch-placeholder">{outdated ? "上次读取" : "使用中"} {devices.length} 台</span>}</div>
        <p>煎药流程仿真 · {description}</p>
      </div>
      <div className="te-task-actions">
        <button className="te-button" disabled={busy || refreshing} onClick={refreshData} aria-label={`刷新使用中${name}`}><ArrowsClockwiseIcon size={18} aria-hidden="true" />{busy || refreshing ? "读取中" : "刷新"}</button>
        <button className="te-button" disabled title="暂无任务报告"><FileTextIcon size={18} aria-hidden="true" />实时报告</button>
        <button className="te-button te-button-danger" disabled title="尚未接入单个任务停止"><StopIcon size={18} aria-hidden="true" />停止</button>
      </div>
    </div>
    <p className="te-pot-data-status" role="status">数据读取时间：{beijingTime(fetched_at)}{outdated && data ? " · 当前显示上次读取结果" : refreshing || busy ? " · 正在更新" : data ? " · 自动更新" : ""}</p>
    {error && <p className="te-pot-error" role="alert">读取失败：{error}。可点击刷新重试。</p>}
    {stale && !error && <p className="te-pot-notice" role="status">数据已过期，等待更新后确认当前{name}状态。</p>}
    {!data ? <p className="te-pot-empty" role="status">{error ? `暂时无法读取${name}状态` : slowConnection ? `平台响应较慢，正在等待${name}状态…` : `正在读取${name}状态…`}</p> : !devices.length ? <p className="te-pot-empty" role="status">{outdated ? `上次读取时没有使用中的${name}` : `当前没有使用中的${name}`}</p> : <div className="te-table-scroll te-pot-table" tabIndex={0} role="region" aria-label={`任务区域${number}使用中${name}列表`}>
      <table><thead><tr><th scope="col">设备</th><th scope="col">状态</th><th scope="col">关联批次 / 工序</th><th scope="col">累计利用率</th><th scope="col">异常 / 等待原因</th></tr></thead><tbody>{devices.map(device => {
        const batch = data.batches.find(item => item.id === device.batch_id);
        const alarms = data.alarms.filter(alarm => alarm.device_id === device.id && alarm.status === "active");
        return <tr key={device.id}>
          <td><strong className="te-pot-code">{device.id}</strong><span className="te-pot-detail">{device.name}</span></td>
          <td><span className="te-pot-busy"><i aria-hidden="true" />使用中</span></td>
          <td>{device.batch_id ? <><span className="te-pot-code">{device.batch_id}</span><span className="te-pot-detail">{batch ? `${batch.current_stage_name ?? labels[batch.status] ?? batch.status} · ${batch.temperature_c} °C · ${batch.progress_percent}%` : "批次详情暂未读取"}</span></> : "未关联批次"}</td>
          <td>{device.utilization_percent}%</td>
          <td className={alarms.length ? "te-pot-error" : undefined}>{alarms.map(alarm => alarm.message).join("；") || batch?.waiting_reason || "—"}</td>
        </tr>;
      })}</tbody></table>
    </div>}
  </article>;
}
