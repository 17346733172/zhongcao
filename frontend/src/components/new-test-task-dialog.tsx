"use client";

import { InfoIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { beijingTime } from "@/lib/data-center-api";
import { useSimulationControls } from "./use-simulation-controls";

export function NewTestTaskDialog({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const previous = useRef<HTMLElement | null>(null);
  const [count, setCount] = useState("5");
  const { status, readError, operationError, success, pending, execute, reload } = useSimulationControls();
  const invalidCount = !/^\d+$/.test(count) || Number(count) < 1 || Number(count) > 50;
  const stale = !!status && (!!readError || Date.now() - Date.parse(status.fetched_at) > 30000);
  const running = status && !stale ? status.clock.running : null;

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    previous.current ??= document.activeElement instanceof HTMLElement ? document.activeElement : null;
    element.showModal();
    return () => {
      element.close();
      requestAnimationFrame(() => { if (!element.isConnected) previous.current?.focus(); });
    };
  }, []);

  return <dialog ref={dialog} className="new-test-task-dialog" aria-labelledby="new-task-title" aria-describedby="new-task-description new-task-preview" aria-busy={!!pending} onCancel={event => { event.preventDefault(); if (!pending) onClose(); }} onKeyDown={event => {
    if (event.key !== "Tab") return;
    const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled])')).filter(element => element.getClientRects().length);
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }} onClick={event => {
    if (pending || event.target !== event.currentTarget) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
  }}>
    <header className="nt-header">
      <div className="nt-heading"><h2 id="new-task-title">全局仿真控制</h2><p id="new-task-description">按现实时间计时：1 秒就是现实 1 秒，调剂 10 分钟需实际运行 10 分钟</p></div>
      <button className="icon-button nt-close" aria-label="关闭全局仿真控制" disabled={!!pending} title={pending ? "请等待当前操作完成" : undefined} onClick={onClose}><XIcon size={22} /></button>
    </header>
    <div className="nt-toolbar">
      <div className="nt-actions">
        <label className="nt-count-field" htmlFor="new-task-count"><span>批次数量</span><input autoFocus id="new-task-count" aria-label="演示批次数量" type="number" min={1} max={50} step={1} disabled={!!pending} value={count} onChange={event => setCount(event.target.value)} aria-invalid={invalidCount || undefined} aria-describedby={`new-task-hint${invalidCount ? " new-task-count-error" : ""}`} /></label>
        <button className="nt-button nt-generate-button" disabled={!!pending || invalidCount} onClick={() => void execute("scenarios", Number(count))}>{pending === "scenarios" ? "正在生成…" : "生成演示数据"}</button>
        <div className="nt-playback-controls"><button className="nt-button" disabled={!!pending || running === true} title={running === true ? "仿真已在运行" : undefined} onClick={() => void execute("start", Number(count))}>{pending === "start" ? "正在开始…" : "开始"}</button><button className="nt-button" disabled={!!pending || running === false} title={running === false ? "仿真已暂停" : undefined} onClick={() => void execute("pause", Number(count))}>{pending === "pause" ? "正在暂停…" : "暂停"}</button></div>
      </div>
    </div>
    <p id="new-task-hint" className="nt-hint">演示批次数量 1–50，每次生成均新增匿名处方和批次，包含常规、包煎、先煎或后下示例；生成后点击「开始」。</p>
    {invalidCount && <p id="new-task-count-error" className="nt-count-error" role="alert">请输入1–50之间的整数批次数量。</p>}
    {pending && <p className="nt-feedback" role="status">正在提交仿真操作，请稍候…</p>}
    {operationError && <p className="nt-feedback nt-operation-error" role="alert">{operationError}</p>}
    {success && <p className="nt-feedback nt-success" role="status">{success}</p>}
    <div className={`nt-status${readError ? " nt-status-error" : ""}`} role={readError ? "alert" : "status"}><InfoIcon size={17} weight="fill" aria-hidden="true" /><p>{readError ? `${readError}${status ? " 当前显示上次成功读取的状态。" : " 尚未取得仿真状态。"}` : !status ? "正在读取仿真状态…" : `${stale ? "上次读取时：" : ""}${status.clock.running ? "正在按真实时间运行。暂停期间不累计工序用时，继续后从原进度运行。" : "已暂停，当前设备分配与工序进度保留。"}`}</p>{(readError || operationError) && <button className="nt-retry" disabled={!!pending} onClick={reload}>重新读取</button>}</div>
    <footer className="nt-footer"><p id="new-task-preview">演示数据仅用于流程仿真。</p><p>数据读取时间：{beijingTime(status?.fetched_at)}</p></footer>
  </dialog>;
}
