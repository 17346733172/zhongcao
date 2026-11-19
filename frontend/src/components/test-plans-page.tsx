"use client";

import { ArrowsClockwiseIcon, HardDrivesIcon } from "@phosphor-icons/react";
import { beijingTime } from "@/lib/data-center-api";
import { useDeviceDefaults } from "@/lib/use-device-defaults";
import { deviceCategories } from "./operations-device-categories";

export function TestPlansPage({ onBusyChange, onSaved }: { onBusyChange: (busy: boolean) => void; onSaved: () => void }) {
  const { data, drafts, reading, pending, error, success, mustReload, readFailed, reload, save, edit, reset } = useDeviceDefaults(onBusyChange, onSaved);
  return <div className="ops-content tp-content">
    <div className="ops-platform-head"><div><h3>设备默认用时</h3><p>按设备分类设置默认每次用时，单位为分钟；同类设备共用设置。</p></div><button className="ops-button" disabled={reading || !!pending} onClick={() => void reload(true)}><ArrowsClockwiseIcon size={18} aria-hidden="true" />{reading ? "读取中" : "重新读取"}</button></div>
    <p className="tp-description">保存后用于后续创建的批次，已创建批次保持原时长。浸泡与煎煮的处方专用工艺参数优先；默认值用于之后新录入的处方。</p>
    <p className="tp-read-time" role="status">数据读取时间：{beijingTime(data?.fetched_at)}{reading && data ? " · 正在更新" : error && data ? " · 当前显示上次读取结果" : ""}</p>
    {data?.notice && !error && <p className="ops-feedback" role="status">{data.notice}</p>}
    {error && <div className="ops-feedback ops-feedback-error" role="alert"><p>{error}{readFailed && " 15 秒后自动重试，也可点击重新读取。"}</p>{data?.notice && <p>{data.notice}</p>}</div>}
    {success && <p className="ops-feedback tp-success" role="status">{success}</p>}
    {!data ? <p className="ops-empty" role="status">{error ? "暂时无法读取设备默认用时，可点击重新读取重试。" : "正在读取设备默认用时…"}</p> : <div className="ops-device-grid">{deviceCategories.map(([kind, name, description]) => {
      const item = data.items.find(item => item.kind === kind);
      const value = drafts[kind] ?? "";
      const minutes = Number(value);
      const invalid = !value.trim() || !Number.isFinite(minutes) || minutes < 0.1 || minutes > 120;
      const changed = !!item && Math.abs(minutes * 60 - item.default_processing_seconds) > 0.00001;
      const disabled = !!pending || reading || !data.supported || !item;
      return <article className="ops-device-card tp-card" key={kind} aria-label={name}>
        <div className="ops-device-head"><HardDrivesIcon size={24} aria-hidden="true" /><h4>{name}</h4></div><p>{description}</p>
        {kind === "pot" ? <p className="ops-device-duration">药锅随整批流程占用，不设置固定每次用时。</p> : <>
          <p className="ops-device-duration">当前默认每次用时：{item ? `${Number((item.default_processing_seconds / 60).toFixed(6))} 分钟` : "未提供"}</p>
          <form onSubmit={event => { event.preventDefault(); if (!disabled && !invalid && changed && !mustReload) void save(kind); }}>
            <label htmlFor={`tp-${kind}`}>默认每次用时（分钟）</label>
            <input id={`tp-${kind}`} type="number" min="0.1" max="120" step="any" inputMode="decimal" value={value} disabled={disabled} aria-invalid={!!item && invalid} aria-describedby={`tp-help-${kind}`} onChange={event => edit(kind, event.target.value)} />
            <small id={`tp-help-${kind}`} className={item && invalid ? "ops-danger" : undefined}>{item && invalid ? "请输入 0.1–120 分钟。" : "可填写 0.1–120 分钟，支持小数。"}</small>
            <div className="tp-actions"><button className="ops-button tp-save" disabled={disabled || invalid || !changed || mustReload} type="submit">{pending === kind ? "保存中…" : "保存"}</button><button className="ops-button" type="button" disabled={disabled || !changed} onClick={() => reset(kind)}>还原当前值</button></div>
          </form>
        </>}
      </article>;
    })}</div>}
    <p className="ops-footnote">仿真参数设置，仅用于当前连接的仿真平台。</p>
  </div>;
}
