"use client";

import { ArrowsClockwiseIcon, XIcon } from "@phosphor-icons/react";
import { Fragment, useEffect, useRef, useState } from "react";
import { errorMessage } from "../lib/api";
import { DATA_CENTER_TIMEOUT_MS, beijingTime, readPrescriptions, type PrescriptionPage } from "../lib/data-center-api";
import { DataDevices, DataOverview, DataStatus, PrescriptionDetails } from "./data-center-panels";
import type { DataCenterTarget } from "../lib/types";
import { DataCenterStatistics } from "./data-center-statistics";
import type { DataCenterSnapshotReader } from "@/lib/use-data-center-snapshot";

const tabs = ["概览", "设备与异常", "全部处方"];
const tabIds = ["overview", "devices", "prescriptions"] as const;

export function DataCenterDialog({ onClose, initialTarget, snapshotReader }: { onClose: () => void; initialTarget?: DataCenterTarget; snapshotReader: DataCenterSnapshotReader }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const previous = useRef<HTMLElement | null>(null);
  const [tab, setTab] = useState<number>(tabIds.indexOf(initialTarget?.tab ?? "overview"));
  const { state, busy: snapshotBusy, slowConnection, refresh, refreshData } = snapshotReader;
  const { data: snapshot, error: snapshotError, fetched_at: updated, refreshing: platformRefreshing, stale: snapshotStale } = state;
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<(PrescriptionPage & { key: string }) | null>(null);
  const [pageBusy, setPageBusy] = useState(false);
  const [pageError, setPageError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  function toggleDetails(id: string, target: HTMLElement) {
    setExpanded(expanded === id ? null : id);
    target.closest(".dc-table-scroll")?.scrollTo({ left: 0 });
  }

  useEffect(() => {
    if (tab !== 2) return;
    const controller = new AbortController();
    setPageBusy(true); setPageError(""); setExpanded(null);
    readPrescriptions(status, offset, AbortSignal.any([controller.signal, AbortSignal.timeout(DATA_CENTER_TIMEOUT_MS)]))
      .then(result => { if (!controller.signal.aborted) {
        if (result.total > 0 && offset >= result.total) { setOffset(Math.floor((result.total - 1) / 20) * 20); return; }
        setPage({ ...result, key: `${status}:${offset}` });
      } })
      .catch(error => { if (!controller.signal.aborted) setPageError(errorMessage(error)); })
      .finally(() => { if (!controller.signal.aborted) setPageBusy(false); });
    return () => controller.abort();
  }, [tab, status, offset, refresh]);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    previous.current ??= document.activeElement instanceof HTMLElement ? document.activeElement : null;
    element.showModal();
    return () => {
      element.close();
      requestAnimationFrame(() => {
        if (element.isConnected) return;
        const mobileMenu = document.querySelector<HTMLElement>('.mobile-menu[aria-label="打开导航"]');
        const target = mobileMenu?.getClientRects().length ? mobileMenu : previous.current;
        target?.focus({ preventScroll: true });
      });
    };
  }, []);

  return <dialog ref={dialog} className="source-dialog data-center-dialog" aria-labelledby="data-center-title" aria-describedby="data-center-description" onCancel={event => { event.preventDefault(); onClose(); }} onKeyDown={event => {
    if (event.key !== "Tab") return;
    const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]),textarea:not([disabled]),select:not([disabled]),[tabindex="0"]')).filter(element => element.getClientRects().length);
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }} onClick={event => {
    if (event.target !== event.currentTarget) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
  }}>
    <header>
      <div><h2 id="data-center-title">数据中心</h2><span className="dc-source">煎药流程仿真</span></div>
      <button autoFocus className="icon-button" aria-label="关闭数据中心" onClick={onClose}><XIcon size={22} /></button>
    </header>
    <div className="dc-toolbar"><div role="tablist" aria-label="数据中心内容">{tabs.map((name, index) => <button key={name} role="tab" id={`dc-tab-${index}`} aria-selected={tab === index} aria-controls="dc-panel" tabIndex={tab === index ? 0 : -1} onClick={() => setTab(index)} onKeyDown={event => {
      const next = event.key === "ArrowRight" ? (index + 1) % tabs.length : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : null;
      if (next == null) return;
      event.preventDefault(); setTab(next); document.getElementById(`dc-tab-${next}`)?.focus();
    }}>{name}</button>)}</div><button className="dc-refresh" aria-label="刷新数据" disabled={snapshotBusy || (tab === 2 && pageBusy)} onClick={refreshData}><ArrowsClockwiseIcon size={16} />{snapshotBusy || (tab === 2 && pageBusy) ? "读取中" : platformRefreshing ? "后台更新中" : "刷新"}</button></div>
    <div className="dc-content" id="dc-panel" role="tabpanel" aria-labelledby={`dc-tab-${tab}`} tabIndex={0}>
      <div className="dc-notice"><p id="data-center-description">数据来自当前连接的仿真平台，仅反映仿真运行情况。</p><span>{snapshotError ? "平台数据更新失败" : platformRefreshing ? "正在后台更新" : updated ? "平台数据已更新" : "正在连接平台"}{updated && ` · 数据读取时间 ${beijingTime(updated)}`} · 后台定时更新</span></div>
      {snapshotError && <div className="dc-error" role="alert">{snapshotError}{snapshot && " 当前显示上次成功读取的数据。"}<button onClick={refreshData}>重试</button></div>}
      {snapshot && snapshotStale && !snapshotError && <p className="dc-loading" role="status">当前显示上次成功读取的数据，后台正在尝试更新。</p>}
      {tab !== 2 && !snapshot && !snapshotError && <p className="dc-empty" role="status">{slowConnection ? "平台响应较慢，正在后台连接。你可以先查看其他标签或关闭窗口。" : "正在读取平台数据…"}</p>}
      {tab === 0 && <DataCenterStatistics refresh={refresh} />}
      {tab === 0 && snapshot && <DataOverview data={snapshot} />}
      {tab === 1 && snapshot && <DataDevices data={snapshot} initialTarget={initialTarget} />}
      {tab === 2 && <>
        <div className="dc-section-heading"><h3>处方信息 <small>{page?.key === `${status}:${offset}` ? `共 ${page.total} 张` : ""}</small></h3><label className="dc-inline-filter">审核状态<select aria-label="审核状态" value={status} onChange={event => { setStatus(event.target.value); setOffset(0); }}><option value="">全部</option><option value="pending_review">待审核</option><option value="approved">已通过</option><option value="rejected">已驳回</option></select></label></div>
        {pageError && <div className="dc-error" role="alert">{pageError}<button onClick={refreshData}>重试</button></div>}
        {pageBusy && <p role="status" className="dc-loading">正在读取处方…</p>}
        {page?.key === `${status}:${offset}` && <>
          <div className="dc-table-scroll" role="region" aria-label="处方列表" tabIndex={0}><table className="dc-prescriptions"><thead><tr><th>外部编号 / 匿名编号</th><th>状态</th><th>药材</th><th>剂数</th><th>录入时间（北京）</th><th>详情</th></tr></thead><tbody>{page.items.map(p => <Fragment key={p.id}><tr><td><button className="dc-text-button dc-code" aria-expanded={expanded === p.id} aria-controls={`dc-detail-${p.id}`} onClick={e => toggleDetails(p.id, e.currentTarget)}>{p.external_no}</button><span className="dc-subtext dc-code">{p.patient_code}</span></td><td><DataStatus status={p.status} /></td><td className="dc-herb-preview">{p.herbs.slice(0, 3).map(h => h.name).join("、")}{p.herbs.length > 3 && ` 等 ${p.herbs.length} 味`}</td><td>{p.doses}</td><td>{beijingTime(p.created_real_time)}</td><td><button className="dc-text-button" aria-expanded={expanded === p.id} aria-controls={`dc-detail-${p.id}`} aria-label={`${expanded === p.id ? "收起" : "查看"}处方 ${p.external_no}`} onClick={e => toggleDetails(p.id, e.currentTarget)}>{expanded === p.id ? "收起" : "查看"}</button></td></tr>{expanded === p.id && <tr id={`dc-detail-${p.id}`}><td colSpan={6}><PrescriptionDetails item={p} data={snapshot} /></td></tr>}</Fragment>)}</tbody></table>{!page.items.length && <p className="dc-empty">暂无符合条件的处方</p>}</div>
          <div className="dc-pagination"><span>{page.total ? `${offset + 1}–${offset + page.items.length} / ${page.total} 张` : "0 张"}</span><div><button disabled={offset === 0 || pageBusy} onClick={() => setOffset(Math.max(0, offset - 20))}>上一页</button><span>{Math.floor(offset / 20) + 1} / {Math.max(1, Math.ceil(page.total / 20))}</span><button disabled={offset + 20 >= page.total || pageBusy} onClick={() => setOffset(offset + 20)}>下一页</button></div></div>
        </>}
      </>}
    </div>
    <footer>仿真数据 · 利用率和吞吐量为仿真统计，不代表实际工厂产能。处方可在平台人工审核。</footer>
  </dialog>;
}
