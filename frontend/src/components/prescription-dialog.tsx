"use client";
import { FileIcon, ImageIcon, UploadSimpleIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { blankPrescription, withDoseScope, preparePrescription, checkPrescription, type Prescription, type PrescriptionStatus, type Preparation, type PrescriptionReport as Report } from "@/lib/prescription-api";
import { PrescriptionDoseScope, PrescriptionFields } from "./prescription-fields";
import { PrescriptionReport } from "./prescription-report";

export function PrescriptionDialog({ onClose }: { onClose: () => void }) {
  const [stage, setStage] = useState<"upload" | "confirm" | "report">("upload");
  const [status, setStatus] = useState<PrescriptionStatus | null>(null);
  const [statusError, setStatusError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  const [text, setText] = useState("");
  const [instruction, setInstruction] = useState("检查这份中药饮片处方的数据完整性和配伍疑点");
  const [preparation, setPreparation] = useState<Preparation | null>(null);
  const [prescription, setPrescription] = useState<Prescription>(blankPrescription);
  const [confirmed, setConfirmed] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const dialog = useRef<HTMLElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const filesInput = useRef<HTMLInputElement>(null);
  const imagesInput = useRef<HTMLInputElement>(null);
  const request = useRef<AbortController | null>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.current?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); closeRef.current(); return; }
      if (event.key !== "Tab") return;
      const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]):not([tabindex="-1"]),textarea:not([disabled]),select:not([disabled]),summary,[tabindex="0"]') ?? []).filter(element => element.getClientRects().length);
      if (!controls.length) { event.preventDefault(); return; }
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog.current)) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", key);
    return () => { document.removeEventListener("keydown", key); request.current?.abort(); const target = previous?.getClientRects().length ? previous : document.querySelector<HTMLElement>(".upload-trigger"); target?.focus(); };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setStatusError("");
    api<PrescriptionStatus>("/prescriptions/status", { signal: controller.signal }).then(setStatus).catch(cause => { if (!controller.signal.aborted) setStatusError(errorMessage(cause)); });
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    content.current?.scrollTo({ top: 0 }); dialog.current?.focus();
    const focusField = content.current?.dataset.focusField;
    if (stage === "confirm" && focusField) {
      delete content.current!.dataset.focusField;
      const field = Array.from(dialog.current?.querySelectorAll<HTMLElement>("[data-field]") ?? []).find(element => element.dataset.field === focusField);
      field?.focus(); field?.scrollIntoView({ block: "center", inline: "center" });
    }
    // Refresh old report contracts with the current data and the user's confirmed scope.
    if (stage === "report" && report && (report.prescription.dose_scope === undefined || !report.conclusion || report.sections?.length !== 5 || !Array.isArray(report.missing_information) || !Array.isArray(report.conclusion?.decision_reasons))) {
      const updated = withDoseScope(report.prescription, report.prescription.dose_scope ?? "per_dose");
      setPrescription(updated); setConfirmed(true); void runCheck(updated);
    }
  }, [stage, report]);
  useEffect(() => {
    if (!file || !/\.(png|jpe?g|webp)$/i.test(file.name)) { setImagePreview(""); return; }
    const url = URL.createObjectURL(file); setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  function choose(files: File[]) {
    if (busy) return;
    if (files.length !== 1) { setError("每次请选择一份处方文件；不要同时混合多个处方或版本。"); return; }
    const selected = files[0];
    if (selected.size > 10 * 1024 * 1024 || !selected.size) { setError("文件为空或超过 10 MB。"); return; }
    if (!/\.(txt|md|docx|pdf|png|jpe?g|webp)$/i.test(selected.name)) { setError("请使用 TXT、MD、DOCX、PDF、PNG、JPG 或 WEBP 文件。"); return; }
    setImagePreview(""); setFile(selected); setText(""); setPreparation(null); setError(""); setFeedback("");
  }
  async function prepare() {
    if (busy || (!file && !text.trim())) return;
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError(""); setFeedback(""); setPreparation(null);
    try {
      const scope = prescription.dose_scope ?? "per_dose";
      const result = await preparePrescription(file, text, instruction, scope, controller.signal);
      if (controller.signal.aborted) return;
      setPreparation(result);
      if (result.prescription) { setPrescription(withDoseScope(result.prescription, scope)); setConfirmed(false); setStage("confirm"); }
      else setError(result.intent.explanation || "请只提供一份可识别的中药饮片处方。");
    } catch (cause) { if (!controller.signal.aborted) setError(errorMessage(cause)); }
    finally { if (!controller.signal.aborted) { setBusy(false); request.current = null; } }
  }
  async function runCheck(value: Prescription) {
    if (busy || request.current || !value.medicines.length) return;
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError(""); setFeedback("");
    try {
      const result = await checkPrescription(value, controller.signal);
      if (controller.signal.aborted) return;
      if (!result.conclusion || result.sections?.length !== 5 || !Array.isArray(result.missing_information) || !Array.isArray(result.conclusion.decision_reasons)) throw new Error("未能生成完整审核报告，请稍后重试。");
      setPrescription(result.prescription); setReport(result); setStage("report");
    } catch (cause) { if (!controller.signal.aborted) setError(errorMessage(cause)); }
    finally { if (!controller.signal.aborted) { setBusy(false); request.current = null; } }
  }
  function review() {
    if (confirmed) void runCheck(prescription);
  }
  function edit(field?: string) {
    if (content.current) content.current.dataset.focusField = field ?? "";
    setStage("confirm"); setConfirmed(false); setFeedback(""); setError("");
  }
  function manual() { setPreparation(null); setPrescription(withDoseScope(blankPrescription(), prescription.dose_scope ?? "per_dose")); setConfirmed(false); setError(""); setFeedback(""); setStage("confirm"); }
  function clearFile() { setFile(null); setImagePreview(""); }
  function startNew() { clearFile(); setText(""); setPreparation(null); setReport(null); setPrescription(blankPrescription()); setConfirmed(false); setStage("upload"); setError(""); setFeedback(""); }
  return <div className="modal-backdrop rx-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="rx-dialog" role="dialog" aria-modal="true" aria-labelledby="rx-title" tabIndex={-1} ref={dialog}>
      <header className="rx-header"><div><h2 id="rx-title">处方检查</h2><p>中药饮片 · 上传识别、核对数据、检查疑点</p></div><button className="icon-button" onClick={onClose} aria-label="关闭处方检查"><XIcon size={22} /></button></header>
      <ol className="rx-steps" aria-label="处方检查步骤">{(["upload", "confirm", "report"] as const).map((step, i) => <li key={step} aria-current={stage === step ? "step" : undefined}><span>{i + 1}</span>{["上传识别", "核对数据", "检查结果"][i]}</li>)}</ol>
      <div className="rx-body" ref={content} aria-busy={busy}>
        {error && <p className="form-error" role="alert">{error}</p>}
        {feedback && <p className="form-success" role="status">{feedback}</p>}
        {stage === "upload" && <>
          <p className="rx-help">每次一份处方、单文件最多 10 MB；PDF 最多 8 页。请使用清晰图片，手写内容必须逐项人工核对。</p>
          <div className="rx-drop" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); choose(Array.from(event.dataTransfer.files)); }}>
            <UploadSimpleIcon size={33} aria-hidden="true" /><p>{file ? file.name : "拖入处方文件或图片"}</p>
            <div className="rx-upload-actions"><button className="auth-secondary" disabled={busy} onClick={() => filesInput.current?.click()}><FileIcon size={18} />上传文件</button><button className="auth-secondary" disabled={busy} onClick={() => imagesInput.current?.click()}><ImageIcon size={18} />上传图片</button>{file && <button className="quiet-button" disabled={busy} onClick={clearFile}>移除文件</button>}</div>
            <span>TXT / MD / DOCX / PDF · PNG / JPG / WEBP</span>
          </div>
          {imagePreview && <img className="rx-image-preview" src={imagePreview} alt="本次上传的处方图片，待核对" />}
          <input ref={filesInput} type="file" className="visually-hidden" tabIndex={-1} aria-label="选择处方文件" accept=".txt,.md,.docx,.pdf" disabled={busy} onChange={event => { if (event.target.files?.length) choose(Array.from(event.target.files)); event.target.value = ""; }} />
          <input ref={imagesInput} type="file" className="visually-hidden" tabIndex={-1} aria-label="选择处方图片" accept=".png,.jpg,.jpeg,.webp" disabled={busy} onChange={event => { if (event.target.files?.length) choose(Array.from(event.target.files)); event.target.value = ""; }} />
          <label className="rx-label">或粘贴处方文字<textarea rows={6} maxLength={20000} disabled={busy || !!file} value={text} onChange={event => { setText(event.target.value); setPreparation(null); setError(""); }} placeholder="请粘贴一份处方，包括药名、剂量、单位、煎法和已知患者信息。" /></label>
          <label className="rx-label">检查说明<input maxLength={500} disabled={busy} value={instruction} onChange={event => setInstruction(event.target.value)} /></label>
          <PrescriptionDoseScope value={prescription} disabled={busy} onChange={value => { setPrescription(value); setConfirmed(false); }} />
          <div className="rx-notice"><strong>文件使用范围</strong><p>图片在本地后端识别；识别文字会发送给已配置的 DeepSeek 做意图识别和提取。处方不加入共享知识库，原文件和结果不持久保存。请先遮盖姓名、证件、联系方式等无关信息。</p></div>
          {statusError ? <p className="form-error" role="alert">{statusError} <button className="quiet-button" onClick={() => setAttempt(value => value + 1)}>重新连接</button></p> : <p className="rx-help">{status ? status.ai_configured ? "识别服务已配置，支持本地图片 OCR。" : "AI 识别尚未配置，可先手动录入并检查数据。" : "正在检查识别服务…"}</p>}
          {preparation && <details open><summary>已读取的原文与识别提示</summary><p>{preparation.intent.explanation}</p><pre className="rx-original">{preparation.source.text}</pre></details>}
        </>}
        {stage === "confirm" && <>
          {imagePreview && <details open><summary>对照原始图片核对</summary><a href={imagePreview} target="_blank" rel="noreferrer">在新窗口放大图片</a><img className="rx-image-preview" src={imagePreview} alt="原始处方图片，请对照下方识别数据" /></details>}
          {preparation && <><p className="rx-notice">已识别为处方检查：{preparation.intent.explanation} · {preparation.prescription?.medicines.length} 味药</p>{preparation.source.notes.map(note => <p key={note} className="rx-notice">{note}</p>)}<details><summary>查看识别原文</summary><pre className="rx-original">{preparation.source.text}</pre></details></>}
          <PrescriptionFields value={prescription} disabled={busy} onChange={value => { setPrescription(value); setConfirmed(false); setError(""); }} />
          <label className="rx-confirm"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} /><span>我已对照原文逐项核对药名、剂量、单位和每剂量口径。</span></label>
        </>}
        {stage === "report" && report && <PrescriptionReport report={report} busy={busy} onSupplement={() => edit(report.missing_information?.[0]?.field)} onFeedback={setFeedback} />}
        {busy && <p className="rx-busy" role="status">{stage === "upload" ? "正在读取文件、识别意图并提取处方，首次图片识别可能需要更长时间…" : "正在检查已确认的处方数据…"}</p>}
      </div>
      <footer className="rx-footer">
        {stage === "upload" ? <><button className="auth-secondary" disabled={busy} onClick={manual}>手动录入</button><button className="auth-primary" disabled={busy || !status?.ai_configured || (!file && !text.trim())} onClick={() => void prepare()}>{busy ? "正在识别…" : "识别并提取处方"}</button></>
          : stage === "confirm" ? <><button className="auth-secondary" disabled={busy} onClick={() => { setStage("upload"); setError(""); }}>返回上传</button><button className="auth-primary" disabled={busy || !confirmed || !prescription.medicines.length} onClick={() => void review()}>{busy ? "正在检查…" : "确认数据并检查"}</button></>
            : <><button className="auth-secondary" disabled={busy} onClick={startNew}>检查另一份处方</button><button className="auth-primary" disabled={busy} onClick={() => edit()}>修改数据后复查</button></>}
      </footer>
    </section>
  </div>;
}
