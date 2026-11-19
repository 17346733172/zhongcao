"use client";

import { HardDrivesIcon, ArrowRightIcon } from "@phosphor-icons/react";
import type { Device } from "@/lib/data-center-api";

export const deviceCategories = [
  ["pot", "煎药锅", "批次全程保留，倒渣与清洗完成后释放。"],
  ["dispenser", "调剂机", "饮片调剂与包煎分包。"],
  ["verification", "复核台", "核对调剂结果，仿真中自动通过。"],
  ["conveyor", "输送单元", "承担药锅输送与常规药组入锅。"],
  ["water", "加水单元", "按批次水量计划进行一煎、二煎加水。"],
  ["soaking", "浸泡工位", "按批次工艺参数进行浸泡。"],
  ["decocter", "煎煮工位", "执行先煎、升温及一煎、二煎工序。"],
  ["filter", "过滤单元", "一煎滤液暂存与两煎药液合并。"],
  ["packer", "包装机", "按处方袋数进行仿真灌装包装。"],
  ["labeler", "贴标机", "为包装成品贴附仿真标签。"],
  ["quality", "质检台", "成品质检，仿真中自动通过。"],
  ["dispatch", "配发台", "配发仿真成品，计入已配发袋数。"],
  ["residue", "倒渣机", "正常生产或取消批次后清除药渣。"],
  ["washer", "清洗机", "完成一方一清洗，清洗后才释放锅具。"],
];
const statuses = [["idle", "空闲"], ["busy", "占用"], ["fault", "故障"], ["offline", "停用"]];
const kinds = deviceCategories;

export function OperationsDeviceCategories({ devices, onSelect }: { devices: Device[]; onSelect: (kind: string) => void }) {
  const extraKinds = [...new Map(devices.filter(device => !kinds.some(([kind]) => kind === device.kind)).map(device => [device.kind, [device.kind, device.kind_name, "平台新增设备类型。"]])).values()];
  return <div className="ops-device-grid">{[...kinds, ...extraKinds].map(([kind, name, description]) => {
    const items = devices.filter(device => device.kind === kind);
    const durations = [...new Set(items.map(device => device.default_processing_seconds))];
    const seconds = durations.length === 1 ? durations[0] : null;
    return <article className="ops-device-card" key={kind} aria-label={name}>
      <div className="ops-device-head"><HardDrivesIcon size={24} aria-hidden="true" /><h4>{name}</h4><span>{items.length} 台</span></div>
      <p>{description}</p>
      {seconds != null && <p className="ops-device-duration">默认每次用时 {Number((seconds / 60).toFixed(2))} 分钟</p>}
      <dl>{statuses.map(([status, label]) => <div key={status}><dt>{label}</dt><dd>{items.filter(device => device.status === status).length}</dd></div>)}</dl>
      <button className="ops-text-button" onClick={() => onSelect(kind)} aria-label={`查看${name}设备与利用率`}>查看设备与利用率 <ArrowRightIcon size={16} aria-hidden="true" /></button>
    </article>;
  })}</div>;
}
