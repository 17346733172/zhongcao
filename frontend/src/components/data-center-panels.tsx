"use client";

import { useState } from "react";
import { beijingTime, labels, simulationTime, type Prescription, type Snapshot } from "../lib/data-center-api";

export function DataStatus({ status }: { status: string }) {
  return <span className={`dc-status dc-status-${status}`}><i aria-hidden="true" />{labels[status] ?? status}</span>;
}

export function DataOverview({ data }: { data: Snapshot }) {
  const { summary: s, devices } = data;
  const metrics = [["处方总数", s.total_prescriptions], ["排队中", s.batch_counts.queued], ["进行中", s.batch_counts.running], ["已暂停", s.batch_counts.paused], ["已完成", s.batch_counts.completed], ["已取消", s.batch_counts.cancelled], ["已配发袋数", s.dispatched_bags], ["活跃报警", s.active_alarms], ["袋 / 运行小时", s.bags_per_virtual_hour]];
  return <>
    <div className="dc-section-heading"><h3>总体指标</h3><span>平台{data.clock.running ? "运行中" : "已暂停"} · 累计运行 {simulationTime(data.clock.now)}</span></div>
    <dl className="dc-metrics">{metrics.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
    <div className="dc-section-heading"><h3>设备概况</h3><span>共 {devices.length} 台</span></div>
    <div className="dc-device-summary">{["busy", "idle", "fault", "offline"].map(status => <div key={status}><DataStatus status={status} /><strong>{devices.filter(d => d.status === status).length}<small> 台</small></strong></div>)}</div>
    <div className="dc-section-heading"><h3>进行中的批次</h3><span>等待资源 {s.waiting_batches} 个</span></div>
    {!data.batches.some(b => ["queued", "running", "paused"].includes(b.status)) ? <p className="dc-empty">暂无进行中的批次</p> : <div className="dc-table-scroll" role="region" aria-label="进行中的批次" tabIndex={0}><table><thead><tr><th>批次</th><th>状态</th><th>当前工序</th><th>进度</th><th>等待原因</th></tr></thead><tbody>{data.batches.filter(b => ["queued", "running", "paused"].includes(b.status)).map(b => <tr key={b.id}><td className="dc-code">{b.id}</td><td><DataStatus status={b.status} /></td><td>{b.current_stage_name ?? "等待分配"}</td><td>{b.progress_percent}%</td><td>{b.waiting_reason ?? "—"}</td></tr>)}</tbody></table></div>}
  </>;
}

export function DataDevices({ data }: { data: Snapshot }) {
  const [kind, setKind] = useState("pot");
  const [status, setStatus] = useState("");
  const [alarmStatus, setAlarmStatus] = useState("active");
  const kinds = Array.from(new Map(data.devices.map(d => [d.kind, d.kind_name])).entries());
  const devices = data.devices.filter(d => (!kind || d.kind === kind) && (!status || d.status === status));
  const alarms = data.alarms.filter(a => !alarmStatus || a.status === alarmStatus);
  return <>
    <div className="dc-section-heading"><h3>设备状态 <small>{devices.length} / {data.devices.length} 台</small></h3><div className="dc-filters"><label>设备类型<select aria-label="设备类型" value={kind} onChange={e => setKind(e.target.value)}><option value="">全部设备</option>{kinds.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label><label>状态<select aria-label="状态" value={status} onChange={e => setStatus(e.target.value)}><option value="">全部状态</option>{["busy", "idle", "fault", "offline"].map(s => <option key={s} value={s}>{labels[s]}</option>)}</select></label></div></div>
    <div className="dc-table-scroll" role="region" aria-label="设备状态列表" tabIndex={0}><table><thead><tr><th>设备</th><th>状态</th><th>关联批次 / 工序</th><th>利用率</th><th>异常 / 等待原因</th></tr></thead><tbody>{devices.map(d => {
      const b = data.batches.find(b => b.id === d.batch_id);
      const alarms = data.alarms.filter(a => a.device_id === d.id && a.status === "active");
      return <tr key={d.id}><td><strong className="dc-code">{d.id}</strong><span className="dc-subtext">{d.name}</span></td><td><DataStatus status={d.status} /></td><td>{d.batch_id ? <><span className="dc-code">{d.batch_id}</span><span className="dc-subtext">{b?.current_stage_name ?? labels[b?.status ?? ""] ?? "等待分配"}{b ? ` · ${b.temperature_c} °C · ${b.progress_percent}%` : ""}</span></> : "—"}</td><td>{d.utilization_percent}%</td><td className={alarms.length ? "dc-danger" : ""}>{alarms.map(a => a.message).join("；") || b?.waiting_reason || (d.status === "fault" ? "设备故障，暂无报警明细" : d.status === "offline" ? "设备已停用" : "—")}</td></tr>;
    })}</tbody></table>{!devices.length && <p className="dc-empty">没有符合条件的设备</p>}</div>
    <div className="dc-section-heading"><h3>报警记录 <small>{alarms.length} 条</small></h3><label className="dc-inline-filter">报警状态<select aria-label="报警状态" value={alarmStatus} onChange={e => setAlarmStatus(e.target.value)}><option value="active">未解除</option><option value="resolved">已解除</option><option value="">全部记录</option></select></label></div>
    {!alarms.length ? <p className="dc-empty">{alarmStatus === "active" ? "当前没有未解除的报警" : "暂无符合条件的报警记录"}</p> : <div className="dc-table-scroll" role="region" aria-label="报警记录" tabIndex={0}><table><thead><tr><th>设备 / 批次</th><th>原因</th><th>状态</th><th>确认</th><th>发生 / 解除（运行时间）</th></tr></thead><tbody>{alarms.map(a => <tr key={a.id}><td>{a.device_id}<span className="dc-subtext dc-code">{a.batch_id ?? "无关联批次"}</span></td><td>{a.message}</td><td><DataStatus status={a.status} /></td><td>{a.acknowledged ? "已确认" : "未确认"}</td><td>{simulationTime(a.created_at)}<span className="dc-subtext">{a.resolved_at == null ? "尚未解除" : simulationTime(a.resolved_at)}</span></td></tr>)}</tbody></table></div>}
  </>;
}

const recipeLabels: Record<string, [string, string]> = { soak_seconds: ["浸泡", "秒"], pre_decoct_seconds: ["先煎", "秒"], heat_seconds: ["升温", "秒"], first_decoct_seconds: ["一煎", "秒"], second_decoct_seconds: ["二煎", "秒"], late_add_seconds: ["后下", "秒"], target_temperature_c: ["目标温度", "°C"], water_ml_per_g: ["加水系数", "ml/g"], evaporation_ml_per_minute: ["蒸发量", "ml/分钟"] };
export function PrescriptionDetails({ item: p, data }: { item: Prescription; data: Snapshot | null }) {
  const b = data?.batches.find(b => b.id === p.batch_id);
  return <div className="dc-prescription-detail">
    <h4>处方详情 · {p.external_no}</h4>
    <dl className="dc-detail-meta"><div><dt>匿名编号</dt><dd>{p.patient_code}</dd></div><div><dt>剂数与包装</dt><dd>{p.doses} 剂 · 每剂 {p.bags_per_dose} 袋 · 每袋 {p.bag_volume_ml} ml</dd></div><div><dt>录入时间（北京）</dt><dd>{beijingTime(p.created_real_time)}</dd></div><div><dt>优先级</dt><dd>{p.priority}</dd></div><div><dt>处方 ID</dt><dd className="dc-code">{p.id}</dd></div><div><dt>批次</dt><dd className="dc-code">{p.batch_id ?? "尚未创建"}</dd></div></dl>
    {b && <p className="dc-detail-line">批次{labels[b.status] ?? b.status} · {b.current_stage_name ?? "无当前工序"} · 进度 {b.progress_percent}% · 温度 {b.temperature_c} °C<br />追溯码：<span className="dc-code">{b.trace_code}</span>{b.waiting_reason && <><br />等待原因：{b.waiting_reason}</>}</p>}
    <div className="dc-table-scroll" role="region" aria-label="处方药材明细" tabIndex={0}><table><thead><tr><th>药材</th><th>每剂量</th><th>合计量</th><th>每剂实测重量</th><th>煎法</th></tr></thead><tbody>{p.herbs.map((h, i) => { const quantity = h.unit === "piece" ? h.quantity_per_dose : h.grams_per_dose; const unit = h.unit === "piece" ? "片" : "g"; return <tr key={i}><td>{h.name}</td><td>{quantity ?? "—"} {unit}</td><td>{quantity == null ? "—" : Number((quantity * p.doses).toFixed(6))} {unit}</td><td>{h.grams_per_dose == null ? "待称重" : `${h.grams_per_dose} g`}</td><td>{labels[h.method] ?? h.method}</td></tr>; })}</tbody></table></div>
    <h4>工艺参数</h4><dl className="dc-recipe">{Object.entries(p.recipe).map(([key, value]) => <div key={key}><dt>{recipeLabels[key]?.[0] ?? key}</dt><dd>{value} {recipeLabels[key]?.[1]}</dd></div>)}</dl>
    <h4>审核记录</h4><p className="dc-detail-line">{p.review ? <>{p.review.approved ? "审核通过" : "审核驳回"} · {p.review.operator} · {beijingTime(p.review.real_time)}<br />{p.review.comment || "无审核备注"}</> : "尚未审核"}</p>
    <h4>处方备注</h4><p className="dc-detail-line">{p.note || "无备注"}</p>
  </div>;
}
