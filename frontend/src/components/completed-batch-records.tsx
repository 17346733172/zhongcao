"use client";

import { ArrowsClockwiseIcon } from "@phosphor-icons/react";
import { beijingTime, labels } from "@/lib/data-center-api";
import { useCompletedBatches } from "@/lib/use-completed-batches";
import type { DataCenterSnapshotReader } from "@/lib/use-data-center-snapshot";

export function CompletedBatchRecords({ snapshotReader }: { snapshotReader: DataCenterSnapshotReader }) {
  const { page, offset, setOffset, busy, slow, error, refreshData } = useCompletedBatches();
  const current = page?.offset === offset ? page : null;
  const { data, fetched_at, stale, error: snapshotError } = snapshotReader.state;
  const outdated = stale || !!snapshotError;

  return <div className="te-running-records te-completed-records">
    <div className="te-records-toolbar">
      <p className="te-pot-data-status" role="status">列表读取时间：{beijingTime(current?.fetched_at)}{error && current ? " · 当前显示上次读取结果" : busy ? " · 正在读取" : current ? " · 自动更新" : ""}{current && <> · 已完成 {current.total} 批</>}</p>
      <button className="te-button" disabled={busy} aria-label="刷新已完成批次记录" onClick={() => { refreshData(); snapshotReader.refreshData(); }}><ArrowsClockwiseIcon size={18} aria-hidden="true" />{busy ? "读取中" : "刷新"}</button>
    </div>
    {data && <p className="te-pot-data-status">累计概览{outdated ? "（上次读取）" : ""}已完成 {data.summary.batch_counts.completed} 批 · 统计读取时间：{beijingTime(fetched_at)}</p>}
    {current && data && current.total !== data.summary.batch_counts.completed && <p className="te-pot-notice">列表与累计概览更新时刻不同，数量暂有差异。</p>}
    {error && <p className="te-pot-error" role="alert">读取失败：{error}。可点击刷新重试。</p>}
    {busy && slow && <p className="te-pot-notice" role="status">平台响应较慢，正在等待已完成批次…</p>}
    {!current ? <p className="te-pot-empty" role="status">{error ? "暂时无法读取本页已完成批次" : "正在读取已完成批次…"}</p> : !current.items.length ? <p className="te-pot-empty" role="status">{error ? "上次读取时没有已完成的批次" : "当前没有已完成的批次"}</p> : <div className="te-table-scroll te-pot-table te-batch-table" tabIndex={0} role="region" aria-label="已完成批次处方记录">
      <table><thead><tr><th scope="col">批次</th><th scope="col">关联处方</th><th scope="col">状态</th><th scope="col">进度</th><th scope="col">追溯码</th></tr></thead><tbody>{current.items.map(batch => <tr key={batch.id}>
        <td className="te-pot-code">{batch.id}</td><td className="te-pot-code">{batch.prescription_id || "未关联处方"}</td>
        <td><span className="te-pot-busy te-batch-completed"><i aria-hidden="true" />{labels[batch.status]}</span></td>
        <td>{batch.progress_percent}%</td><td className="te-pot-code">{batch.trace_code || "未记录"}</td>
      </tr>)}</tbody></table>
    </div>}
    {page && <div className="te-records-pagination" aria-label="已完成批次分页">
      <span>{current ? current.total ? `${offset + 1}–${offset + current.items.length} / ${current.total} 批` : "0 批" : `第 ${Math.floor(offset / 20) + 1} 页尚未读取`}</span>
      <div><button className="te-button" disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>上一页</button><span>{Math.floor(offset / 20) + 1} / {Math.max(1, Math.ceil(page.total / 20))}</span><button className="te-button" disabled={busy || !current || offset + 20 >= current.total} onClick={() => setOffset(offset + 20)}>下一页</button></div>
    </div>}
  </div>;
}
