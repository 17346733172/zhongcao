"use client";

import { ArrowRightIcon, DownloadSimpleIcon, FileTextIcon, ListChecksIcon, PlayIcon, StopIcon } from "@phosphor-icons/react";
import { useRef, useState, type KeyboardEvent } from "react";

const tabs = [{ id: "running", label: "执行中" }, { id: "history", label: "历史批次" }, { id: "records", label: "测试记录" }] as const;
type Tab = (typeof tabs)[number]["id"];
const recordColumns = ["结束时间", "run_id", "机台#槽位", "序列号", "判定", "不合格项", "Rθ °C/W", "T0−T1 °C"];
const historyColumns = ["批次编号", "测试方案 / 版本", "开始时间", "结束时间", "测试数量", "良率", "报告"];

export function TestExecutionHeader({ onNewTask, newTaskOpen }: { onNewTask: () => void; newTaskOpen: boolean }) {
  return <>
    <div className="te-page-heading"><h2 id="workspace-module-title">测试执行</h2><p>下发方案并开始连续生产 · 跟踪批次进度 · 历史批次与报告</p></div>
    <div className="te-header-actions"><button className="te-button" disabled title="暂无可导出的测试结果"><DownloadSimpleIcon size={18} aria-hidden="true" />导出结果表</button><button className="te-button te-button-primary" aria-haspopup="dialog" aria-expanded={newTaskOpen} onClick={onNewTask}><PlayIcon size={18} aria-hidden="true" />新建测试任务</button></div>
  </>;
}

function TaskLayoutPlaceholder({ number }: { number: string }) {
  return <article className="te-task-card" aria-label={`任务布局占位 ${number}`}>
    <div className="te-task-heading"><div className="te-task-context"><div className="te-task-title"><h3>任务区域 {number}</h3><span className="te-status">内容待补充</span><span className="te-batch-placeholder">批次编号待补充</span></div><p>测试方案 · 版本 · 开始时间 · 预计剩余：待补充</p></div><div className="te-task-actions"><button className="te-button" disabled title="暂无任务报告"><FileTextIcon size={18} aria-hidden="true" />实时报告</button><button className="te-button te-button-danger" disabled title="尚未接入执行任务"><StopIcon size={18} aria-hidden="true" />停止</button></div></div>
    <div className="te-task-summary"><div className="te-quantity"><strong>—</strong><span>/ —</span><span>测试数量待补充</span></div><dl className="te-results"><div className="te-pass"><dt>通过</dt><dd>—</dd></div><div className="te-fail"><dt>不合格</dt><dd>—</dd></div><div className="te-aborted"><dt>中止</dt><dd>—</dd></div><div><dt>良率</dt><dd>—</dd></div></dl></div>
    <div className="te-progress-placeholder" aria-label="测试进度待补充" />
    <div className="te-machine-placeholders" aria-label="机台与槽位待补充"><span>机台待补充</span><span>槽位待补充</span><span>执行状态待补充</span></div>
  </article>;
}

function EmptyRecordsTable({ history = false }: { history?: boolean }) {
  const columns = history ? historyColumns : recordColumns;
  return <><div className="te-table-scroll" tabIndex={0} role="region" aria-label={history ? "历史批次列表" : "测试记录列表"}>
    <table><thead><tr>{columns.map(column => <th key={column} scope="col">{column}</th>)}</tr></thead><tbody /></table>
  </div><div className="te-records-empty"><ListChecksIcon size={27} aria-hidden="true" /><span>{history ? "历史批次内容待补充" : "测试记录内容待补充"}</span><small>暂无已接入的数据</small></div></>;
}

export function TestExecutionPage() {
  const [tab, setTab] = useState<Tab>("running");
  const tablist = useRef<HTMLDivElement>(null);
  function selectTab(id: Tab) {
    setTab(id);
    tablist.current?.querySelector<HTMLButtonElement>(`#te-tab-${id}`)?.focus();
  }
  function tabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === "ArrowRight" ? (index + 1) % tabs.length : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : null;
    if (next == null) return;
    event.preventDefault();
    selectTab(tabs[next].id);
  }

  return <div className="te-content">
    <p className="te-preview-note"><span>布局预览</span>任务、进度与测试记录内容待补充。</p>
    <div ref={tablist} className="te-tabs" role="tablist" aria-label="测试执行内容">{tabs.map(({ id, label }, index) => <button key={id} id={`te-tab-${id}`} role="tab" aria-selected={tab === id} aria-controls="te-panel" tabIndex={tab === id ? 0 : -1} onClick={() => selectTab(id)} onKeyDown={event => tabKey(event, index)}>{label}{id !== "records" && <span className="te-tab-count" aria-label="数量待补充">—</span>}</button>)}</div>
    <div id="te-panel" role="tabpanel" aria-labelledby={`te-tab-${tab}`} tabIndex={0}>
      {tab === "running" ? <>
        <div className="te-task-list"><TaskLayoutPlaceholder number="01" /><TaskLayoutPlaceholder number="02" /></div>
        <section className="te-records-section" aria-labelledby="te-live-title"><div className="te-records-heading"><h3 id="te-live-title"><ListChecksIcon size={20} aria-hidden="true" />实时测试记录 <small>RUNS · STREAM</small></h3><button className="te-all-records" onClick={() => selectTab("records")}>全部记录 <ArrowRightIcon size={17} aria-hidden="true" /></button></div><EmptyRecordsTable /></section>
      </> : tab === "history" ? <section className="te-records-section" aria-labelledby="te-history-title"><div className="te-records-heading"><h3 id="te-history-title">历史批次</h3></div><EmptyRecordsTable history /></section> : <section className="te-records-section" aria-labelledby="te-records-title"><div className="te-records-heading"><h3 id="te-records-title"><ListChecksIcon size={20} aria-hidden="true" />测试记录</h3></div><EmptyRecordsTable /></section>}
    </div>
  </div>;
}
