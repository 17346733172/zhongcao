import { api } from "./api";

export type DoseScope = "per_dose" | "total" | "unknown";
export type Medicine = { name: string; dose: string; unit: string; method: string; dose_scope: DoseScope; source: string };
export type Prescription = { dose_scope?: DoseScope; age: number | null; sex: "male" | "female" | "unknown"; pregnancy: "yes" | "no" | "unknown"; diagnosis: string; allergies: string; regimen: string; doses: number | null; medicines: Medicine[] };
export type PrescriptionStatus = { framework: string; ai_configured: boolean; formats: string[]; max_bytes: number; max_text: number; max_pdf_pages: number; ocr: string; persistence: string };
export type Preparation = {
  status: "needs_confirmation" | "needs_clarification";
  source: { text: string; method: string; notes: string[]; confidence: number | null; pages: number };
  intent: { kind: string; explanation: string; multiple_prescriptions: boolean };
  prescription: Prescription | null; steps: string[]; framework: string; model: string;
};
export type Finding = { code: string; level: "error" | "risk" | "missing" | "review"; title: string; detail: string; medicines: string[]; basis: string; url: string | null; blocking: boolean };
export type AuditConclusion = { status: "passed" | "not_passed" | "needs_information"; result: string; detail: string; finding_codes: string[]; decision_reasons: string[]; note: string };
export type ReportItem = { text: string; lead: string; children: string[]; sources: { label: string; url: string }[] };
export type ReportSection = { number: "3.1" | "3.2" | "3.3" | "3.4" | "3.5"; title: string; paragraphs: ReportItem[]; items: ReportItem[]; ordered: boolean };
export type MissingInformation = { field: string; label: string; prompt: string };
export type PrescriptionReport = { status: string; title: string; conclusion?: AuditConclusion; sections?: ReportSection[]; missing_information?: MissingInformation[]; prescription: Prescription; findings: Finding[]; counts: Record<Finding["level"], number>; steps: string[]; framework: string; rules_version: string; scope: string[]; limitations: string[] };
export const findingLabels: Record<Finding["level"], string> = { error: "数据异常", risk: "配伍 / 用药疑点", missing: "信息缺失", review: "待人工复核" };
export const doseScopeLabels = { per_dose: "每剂量", total: "总量", unknown: "口径未知" };
export const blankMedicine = (scope: DoseScope = "per_dose"): Medicine => ({ name: "", dose: "", unit: "", method: "", dose_scope: scope, source: "" });
export const blankPrescription = (): Prescription => ({ dose_scope: "per_dose", age: null, sex: "unknown", pregnancy: "unknown", diagnosis: "", allergies: "", regimen: "", doses: null, medicines: [blankMedicine()] });
export function withDoseScope(prescription: Prescription, scope: DoseScope): Prescription {
  return { ...prescription, dose_scope: scope, medicines: prescription.medicines.map(item => scope === "unknown" ? { ...item } : { ...item, dose_scope: scope }) };
}
export function preparePrescription(file: File | null, text: string, instruction: string, scope: DoseScope, signal: AbortSignal) {
  const data = new FormData();
  if (file) data.set("file", file); else data.set("text", text);
  data.set("instruction", instruction);
  data.set("dose_scope", scope);
  return api<Preparation>("/prescriptions/prepare", { method: "POST", body: data, signal: AbortSignal.any([signal, AbortSignal.timeout(180000)]) });
}
export function checkPrescription(prescription: Prescription, signal: AbortSignal) {
  const normalized = withDoseScope(prescription, prescription.dose_scope ?? "per_dose");
  return api<PrescriptionReport>("/prescriptions/check", { method: "POST", body: JSON.stringify({ prescription: normalized, confirmed: true }), signal: AbortSignal.any([signal, AbortSignal.timeout(30000)]) });
}
export function prescriptionReportText(report: PrescriptionReport) {
  const inline = (value: string) => value.replace(/\s+/g, " ").replace(/[\\`*_[\]<>#]/g, "\\$&");
  const content = (item: ReportItem) => (item.lead ? `**${inline(item.lead)}** ` : "") + inline(item.text)
    + (item.sources.length ? "（" + item.sources.map(source => `[${inline(source.label)}](${source.url})`).join("、") + "）" : "");
  return (report.sections ?? []).map(section => [
    `### ${section.number} ${inline(section.title)}`,
    ...section.paragraphs.map(content),
    section.items.map((item, index) => `${section.ordered ? `${index + 1}.` : "-"} ${content(item)}`
      + item.children.map(child => `\n   - ${inline(child)}`).join("")).join("\n"),
  ].filter(Boolean).join("\n\n")).join("\n\n");
}
