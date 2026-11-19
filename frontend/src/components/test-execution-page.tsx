"use client";

import { ArrowRightIcon, DownloadSimpleIcon, ListChecksIcon, PlayIcon } from "@phosphor-icons/react";
import { useRef, useState, type KeyboardEvent } from "react";
import type { DataCenterSnapshotReader } from "@/lib/use-data-center-snapshot";
import { ActiveDevicesTask } from "./active-devices-task";
import { RunningBatchRecords } from "./running-batch-records";
import { CompletedBatchRecords } from "./completed-batch-records";

const tabs = [{ id: "running", label: "执行中" }, { id: "history", label: "历史批次" }, { id: "records", label: "测试记录" }] as const;
type Tab = (typeof tabs)[number]["id"];

export function TestExecutionHeader({ onNewTask, newTaskOpen }: { onNewTask: () => void; newTaskOpen: boolean }) {
  return <>
    <div className="te-page-heading"><h2 id="workspace-module-title">测试执行</h2><p>下发方案并开始连续生产 · 跟踪批次进度 · 历史批次与报告</p></div>
    <div className="te-header-actions"><button className="te-button" disabled title="暂无可导出的测试结果"><DownloadSimpleIcon size={18} aria-hidden="true" />导出结果表</button><button className="te-button te-button-primary" aria-haspopup="dialog" aria-expanded={newTaskOpen} onClick={onNewTask}><PlayIcon size={18} aria-hidden="true" />新建测试任务</button></div>
  </>;
}

export function TestExecutionPage({ snapshotReader }: { snapshotReader: DataCenterSnapshotReader }) {
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
    <p className="te-preview-note"><span>仿真数据</span>任务区域 01 展示使用中的药锅，区域 02 展示其余使用中的设备；测试记录展示进行中批次，历史批次展示当前平台已完成批次及关联处方。测试结果与报告待接入。</p>
    <div ref={tablist} className="te-tabs" role="tablist" aria-label="测试执行内容">{tabs.map(({ id, label }, index) => <button key={id} id={`te-tab-${id}`} role="tab" aria-selected={tab === id} aria-controls="te-panel" tabIndex={tab === id ? 0 : -1} onClick={() => selectTab(id)} onKeyDown={event => tabKey(event, index)}>{label}{id !== "records" && <span className="te-tab-count" aria-label={id === "history" && snapshotReader.state.data ? `${snapshotReader.state.stale || snapshotReader.state.error ? "上次" : "当前"}累计统计已完成批次数量` : "数量待补充"}>{id === "history" ? snapshotReader.state.data?.summary.batch_counts.completed ?? "—" : "—"}</span>}</button>)}</div>
    <div id="te-panel" role="tabpanel" aria-labelledby={`te-tab-${tab}`} tabIndex={0}>
      {tab === "running" ? <>
        <div className="te-task-list"><ActiveDevicesTask snapshotReader={snapshotReader} group="pots" /><ActiveDevicesTask snapshotReader={snapshotReader} group="other" /></div>
        <section className="te-records-section" aria-labelledby="te-live-title"><div className="te-records-heading"><h3 id="te-live-title"><ListChecksIcon size={20} aria-hidden="true" />实时测试记录 <small>RUNS · STREAM</small></h3><button className="te-all-records" onClick={() => selectTab("records")}>全部记录 <ArrowRightIcon size={17} aria-hidden="true" /></button></div><RunningBatchRecords snapshotReader={snapshotReader} /></section>
      </> : tab === "history" ? <section className="te-records-section" aria-labelledby="te-history-title"><div className="te-records-heading"><h3 id="te-history-title">历史批次</h3></div><CompletedBatchRecords snapshotReader={snapshotReader} /></section> : <section className="te-records-section" aria-labelledby="te-records-title"><div className="te-records-heading"><h3 id="te-records-title"><ListChecksIcon size={20} aria-hidden="true" />测试记录</h3></div><RunningBatchRecords snapshotReader={snapshotReader} /></section>}
    </div>
  </div>;
}
