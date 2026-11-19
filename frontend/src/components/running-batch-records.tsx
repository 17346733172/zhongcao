"use client";

import { ArrowsClockwiseIcon } from "@phosphor-icons/react";
import { beijingTime, labels } from "@/lib/data-center-api";
import type { DataCenterSnapshotReader } from "@/lib/use-data-center-snapshot";

export function RunningBatchRecords({ snapshotReader }: { snapshotReader: DataCenterSnapshotReader }) {
  const { state, busy, slowConnection, refreshData } = snapshotReader;
  const { data, fetched_at, stale, error, refreshing } = state;
  const batches = data?.batches.filter(batch => batch.status === "running") ?? [];
  const outdated = stale || !!error;

  return <div className="te-running-records">
    <div className="te-records-toolbar">
      <p className="te-pot-data-status" role="status">数据读取时间：{beijingTime(fetched_at)}{outdated && data ? " · 当前显示上次读取结果" : refreshing || busy ? " · 正在更新" : data ? " · 自动更新" : ""}{data && <> · {outdated ? "上次读取进行中" : "进行中"} {batches.length} 批</>}</p>
      <button className="te-button" disabled={busy || refreshing} onClick={refreshData} aria-label="刷新进行中批次记录"><ArrowsClockwiseIcon size={18} aria-hidden="true" />{busy || refreshing ? "读取中" : "刷新"}</button>
    </div>
    {error && <p className="te-pot-error" role="alert">读取失败：{error}。可点击刷新重试。</p>}
    {stale && !error && <p className="te-pot-notice" role="status">数据已过期，等待更新后确认当前批次状态。</p>}
    {!data ? <p className="te-pot-empty" role="status">{error ? "暂时无法读取进行中的批次" : slowConnection ? "平台响应较慢，正在等待批次记录…" : "正在读取批次记录…"}</p> : !batches.length ? <p className="te-pot-empty" role="status">{outdated ? "上次读取时没有进行中的批次" : "当前没有进行中的批次"}</p> : <div className="te-table-scroll te-pot-table te-batch-table" tabIndex={0} role="region" aria-label="进行中批次处方记录">
      <table><thead><tr><th scope="col">批次</th><th scope="col">关联处方</th><th scope="col">状态</th><th scope="col">当前工序</th><th scope="col">进度</th><th scope="col">等待原因</th></tr></thead><tbody>{batches.map(batch => <tr key={batch.id}>
        <td className="te-pot-code">{batch.id}</td>
        <td className="te-pot-code">{batch.prescription_id || "未关联处方"}</td>
        <td><span className="te-pot-busy"><i aria-hidden="true" />{labels[batch.status]}</span></td>
        <td>{batch.current_stage_name ?? "等待分配"}</td>
        <td>{batch.progress_percent}%</td>
        <td>{batch.waiting_reason ?? "—"}</td>
      </tr>)}</tbody></table>
    </div>}
  </div>;
}
