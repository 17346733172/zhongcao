import { api } from "./api";

export type Device = { id: string; name: string; kind: string; kind_name: string; status: string; batch_id: string | null; capacity_ml: number; utilization_percent: number };
export type Batch = { id: string; prescription_id: string; status: string; current_stage_name: string | null; progress_percent: number; temperature_c: number; waiting_reason: string | null; trace_code: string };
export type Alarm = { id: string; device_id: string; batch_id: string | null; message: string; status: string; acknowledged: boolean; created_at: number; resolved_at: number | null };
export type Snapshot = {
  clock: { now: number; running: boolean; speed: number };
  summary: { total_prescriptions: number; batch_counts: Record<"queued" | "running" | "paused" | "completed" | "cancelled", number>; dispatched_bags: number; active_alarms: number; waiting_batches: number; bags_per_virtual_hour: number };
  devices: Device[]; batches: Batch[]; alarms: Alarm[];
};
export type Prescription = {
  id: string; external_no: string; patient_code: string; status: string; priority: number; doses: number; bags_per_dose: number; bag_volume_ml: number;
  herbs: { name: string; unit: string; grams_per_dose: number | null; quantity_per_dose: number | null; method: string }[];
  batch_id: string | null; created_at: number; created_real_time: string | null; recipe: Record<string, number>;
  review: { approved: boolean; operator: string; comment: string; real_time?: string } | null; note: string;
};
export type PrescriptionPage = { items: Prescription[]; total: number; offset: number; limit: number };
export const readSnapshot = (signal: AbortSignal) => api<Snapshot>("/data-center/snapshot", { signal });
export const readPrescriptions = (status: string, offset: number, signal: AbortSignal) => api<PrescriptionPage>(`/data-center/prescriptions?offset=${offset}&limit=20${status ? `&status=${encodeURIComponent(status)}` : ""}`, { signal });
export const labels: Record<string, string> = { idle: "空闲", busy: "使用中", fault: "故障", offline: "已停用", queued: "排队中", running: "进行中", paused: "已暂停", completed: "已完成", cancelled: "已取消", pending_review: "待审核", approved: "已通过", rejected: "已驳回", active: "未解除", resolved: "已解除", normal: "常规", pre_decoct: "先煎", late_add: "后下", bag: "包煎" };
export function beijingTime(value?: string | null) {
  if (!value) return "未记录";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "未记录" : new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}
export function simulationTime(seconds: number) { return `${(seconds / 3600).toFixed(2)} 小时`; }
