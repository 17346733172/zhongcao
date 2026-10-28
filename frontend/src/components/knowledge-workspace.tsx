"use client";

import { ListIcon, UploadSimpleIcon } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { initialConversations, initialDocuments, libraries } from "@/lib/demo-data";
import { createAnswer } from "@/lib/knowledge-answer";
import { generateAnswer, loadAIStatus, type AIStatus } from "@/lib/chat-api";
import { answerModeInfo, runAnswerMode, toggleAnswerOption } from "@/lib/answer-mode";
import type { AnswerMode, AnswerOption, Conversation, KnowledgeDocument, Source } from "@/lib/types";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "./authenticated";
import { Sidebar } from "./sidebar";
import { ConversationView } from "./conversation-view";
import { QuestionComposer } from "./question-composer";
import { UploadPanel } from "./upload-panel";
import { SourceDialog } from "./source-dialog";
import { ReferenceDocumentDialog } from "./reference-document-dialog";

export default function KnowledgeWorkspace() {
  const { user } = useAuth();
  const canWrite = user.permissions.includes("knowledge:write");
  const [uploading, setUploading] = useState(false);
  const [documentError, setDocumentError] = useState("");
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [libraryId, setLibraryId] = useState("herbal");
  const [conversations, setConversations] = useState<Conversation[]>(initialConversations);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>(initialDocuments);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [uploadsOpen, setUploadsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<AnswerMode>("extract");
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [aiStatusError, setAIStatusError] = useState("");
  const [answerError, setAnswerError] = useState("");
  const modeChosen = useRef(false);
  const [source, setSource] = useState<Source | null>(null);
  const [referenceOpen, setReferenceOpen] = useState(false);
  const [referenceDocument, setReferenceDocument] = useState<Source | null>(null);
  const [toast, setToast] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const answerRequest = useRef<AbortController | null>(null);
  const currentLibrary = libraries.find((item) => item.id === libraryId)!;
  const currentConversation = conversations.find((item) => item.id === activeId);
  const libraryDocuments = documents.filter((item) => item.libraryId === libraryId);
  const closeSource = useCallback(() => setSource(null), []);
  const closeReference = useCallback(() => setReferenceOpen(false), []);
  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    setDocumentError("");
    try {
      const [stored, reference] = await Promise.all([
        api<KnowledgeDocument[]>("/documents"),
        api<Source>("/reference-document"),
      ]);
      setDocuments((current) => [...current.filter((doc) => !doc.stored), ...stored]);
      setReferenceDocument(reference);
    } catch (cause) { setDocumentError(errorMessage(cause)); }
    finally { setDocumentsLoading(false); }
  }, []);
  useEffect(() => { void loadDocuments(); }, [loadDocuments]);
  useEffect(() => {
    let active = true;
    loadAIStatus().then((status) => {
      if (!active) return;
      setAIStatus(status);
      if (status.configured && !modeChosen.current) setMode("ai");
    }).catch(() => { if (active) setAIStatusError("AI 状态暂时无法读取，仍可使用原文检索。"); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const small = window.matchMedia("(max-width: 720px)");
    const adapt = () => {
      setMobile(small.matches);
      setNavigationOpen(false);
      setUploadsOpen(false);
    };
    adapt();
    small.addEventListener("change", adapt);
    return () => small.removeEventListener("change", adapt);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (currentConversation?.messages.length) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [currentConversation?.messages.length, activeId, busy]);

  useEffect(() => {
    function escape(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape" || source || referenceOpen) return;
      setNavigationOpen(false);
      setUploadsOpen(false);
    }
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [source, referenceOpen]);

  useEffect(() => {
    const selector = navigationOpen && mobile ? ".sidebar" : uploadsOpen ? ".upload-panel" : null;
    if (!selector) return;
    const panel = document.querySelector<HTMLElement>(selector);
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const visibleControls = () => Array.from(panel?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]):not([tabindex="-1"]), select:not([disabled]), [tabindex="0"]') ?? []).filter((element) => element.getClientRects().length);
    visibleControls()[0]?.focus();
    function containFocus(event: globalThis.KeyboardEvent) {
      if (event.key !== "Tab" || document.querySelector('.source-dialog[role="dialog"][aria-modal="true"]')) return;
      const controls = visibleControls();
      const first = controls[0], last = controls[controls.length - 1];
      if (!first) return;
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", containFocus);
    return () => { document.removeEventListener("keydown", containFocus); previous?.focus(); };
  }, [navigationOpen, uploadsOpen, mobile]);

  function cancelPending() {
    answerRequest.current?.abort();
    answerRequest.current = null;
    setBusy(false);
    setAnswerError("");
  }
  function newConversation() {
    cancelPending();
    setActiveId(null);
    setDraft("");
    setNavigationOpen(false);
    requestAnimationFrame(() => composerRef.current?.focus());
  }
  function selectLibrary(id: string) {
    setLibraryId(id);
    setReferenceOpen(true);
  }
  function selectConversation(id: string) {
    cancelPending();
    setActiveId(id);
    setDraft("");
    setNavigationOpen(false);
  }
  async function ask(question: string) {
    const text = question.trim();
    if (!text || busy || answerRequest.current || documentsLoading || documentError) return;
    if (mode === "none") {
      setAnswerError("请选择 AI 回答或原文检索后再发送。");
      return;
    }
    const controller = new AbortController();
    answerRequest.current = controller;
    setBusy(true);
    setAnswerError("");
    setDraft(text);
    const conversationId = activeId ?? crypto.randomUUID();
    const time = "今天 " + new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
    try {
      const result = await runAnswerMode(mode, text,
        (question) => generateAnswer(question, controller.signal, currentConversation?.messages ?? []),
        (question) => createAnswer(question, libraryDocuments, referenceDocument ?? undefined),
      );
      if (controller.signal.aborted || answerRequest.current !== controller) return;
      const message = { id: crypto.randomUUID(), question: text, ...result, time };
      setConversations((current) => {
        const exists = current.find((item) => item.id === conversationId);
        if (exists) return current.map((item) => item.id === conversationId ? { ...item, messages: [...item.messages, message] } : item);
        return [{ id: conversationId, libraryId, title: text.slice(0, 16), messages: [message] }, ...current];
      });
      setActiveId(conversationId);
      setDraft("");
    } catch (cause) {
      if (!controller.signal.aborted && answerRequest.current === controller) setAnswerError(errorMessage(cause));
    } finally {
      if (answerRequest.current === controller) {
        answerRequest.current = null;
        setBusy(false);
        requestAnimationFrame(() => composerRef.current?.focus());
      }
    }
  }
  function chooseMode(option: AnswerOption) {
    if (busy) return;
    modeChosen.current = true;
    setMode((current) => toggleAnswerOption(current, option));
    setAnswerError("");
  }
  function submit(event: FormEvent) { event.preventDefault(); void ask(draft); }
  function composerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void ask(draft);
    }
  }
  async function addFiles(files: File[]) {
    if (!files.length || !canWrite || uploading || documentsLoading) return;
    setUploadsOpen(true);
    setUploading(true);
    for (const file of files) {
      const base: KnowledgeDocument = { id: crypto.randomUUID(), libraryId, name: file.name, status: "parsing", progress: 0, content: "", demo: false };
      setDocuments((current) => [...current, base]);
      let result: KnowledgeDocument;
      if (!/\.(md|txt|pdf|docx)$/i.test(file.name)) result = { ...base, status: "error", error: "格式不支持，请选择 MD、TXT、PDF 或 Word" };
      else if (file.size > 10 * 1024 * 1024) result = { ...base, status: "error", error: "文件超过 10 MB 限制" };
      else if (!/\.(md|txt)$/i.test(file.name)) result = { ...base, status: "needs-parser", progress: 100 };
      else {
        try {
          const content = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()).replace(/^\uFEFF/, "");
          if (!content.trim()) throw new Error("资料内容为空");
          result = await api<KnowledgeDocument>("/documents", { method: "POST", body: JSON.stringify({ name: file.name, content }) });
          setToast("文本资料已保存到共享知识库");
        } catch (cause) { result = { ...base, status: "error", error: cause instanceof TypeError ? "请使用 UTF-8 编码的文本文件" : errorMessage(cause) }; }
      }
      setDocuments((current) => current.map((doc) => doc.id === base.id ? result : doc));
    }
    setUploading(false);
  }
  async function removeDocument(id: string) {
    if (!canWrite || uploading || documentsLoading) return;
    const doc = documents.find((item) => item.id === id);
    try {
      if (doc?.stored) await api<void>(`/documents/${id}`, { method: "DELETE" });
      setDocuments((current) => current.filter((item) => item.id !== id));
      setToast(doc?.stored ? "资料已从共享知识库移除" : "已移除本页条目");
    } catch (cause) { setToast(errorMessage(cause)); }
  }
  function previewDocument(doc: KnowledgeDocument) {
    setSource({ id: doc.id, name: doc.name, excerpt: doc.content.slice(0, 300), fullText: doc.content, demo: doc.demo });
  }
  function attach() {
    if (!canWrite || uploading) return;
    setUploadsOpen(true);
    inputRef.current?.click();
  }

  return (
    <div className={"workspace" + (!uploadsOpen ? " uploads-hidden" : "") + (sidebarCollapsed ? " nav-collapsed" : "")}>
      {navigationOpen && <button className="drawer-backdrop navigation-backdrop" aria-label="关闭导航遮罩" onClick={() => setNavigationOpen(false)} />}
      {uploadsOpen && <button className="drawer-backdrop upload-backdrop" aria-label="关闭上传遮罩" onClick={() => setUploadsOpen(false)} />}
      <Sidebar libraryId={libraryId} activeId={activeId} conversations={conversations} open={navigationOpen} onLibrary={selectLibrary} onConversation={selectConversation} onNew={newConversation} onClose={() => setNavigationOpen(false)} onCollapse={() => setSidebarCollapsed(true)} />
      <main className="main-panel" id="main-content" inert={!!source || referenceOpen || (navigationOpen && mobile) || uploadsOpen}>
        <header className="main-header">
          <button className={"icon-button mobile-menu" + (sidebarCollapsed ? " desktop-visible" : "")} aria-label={mobile ? "打开导航" : "展开侧栏"} aria-expanded={mobile ? navigationOpen : !sidebarCollapsed} onClick={() => mobile ? setNavigationOpen(true) : setSidebarCollapsed(false)}><ListIcon size={25} /></button>
          <div className="header-context">
            <div className="breadcrumb"><span className="breadcrumb-root">知识库<span className="breadcrumb-slash">/</span></span><h1>{currentLibrary.name}</h1><span className="demo-label">{answerModeInfo[mode].label}</span></div>
            <p>{answerModeInfo[mode].description}</p>
          </div>
          <button className="upload-trigger" aria-label={canWrite ? "上传资料" : "查看资料"} onClick={() => setUploadsOpen(true)} aria-expanded={uploadsOpen}><UploadSimpleIcon size={22} aria-hidden="true" /><span>{canWrite ? "上传资料" : "查看资料"}</span></button>
        </header>
        {(documentsLoading || documentError) && <div className="document-feedback" role={documentError ? "alert" : "status"}><span>{documentError || "正在读取知识库资料…"}</span>{documentError && <button onClick={() => void loadDocuments()}>重新读取</button>}</div>}
        <div className={"chat-body" + (!(currentConversation?.messages.length) ? " welcome-state" : "")}>
          <div ref={scrollRef} className="conversation-scroll" aria-label="问答内容" aria-busy={busy}>
            <ConversationView mode={mode} messages={currentConversation?.messages ?? []} busy={busy} libraryName={currentLibrary.name} onSource={setSource} onToast={setToast} />
          </div>
          <QuestionComposer draft={draft} mode={mode} busy={busy} disabled={documentsLoading || !!documentError} canWrite={canWrite} uploading={uploading} error={answerError} status={aiStatus} statusError={aiStatusError} inputRef={composerRef} onDraft={setDraft} onMode={chooseMode} onSubmit={submit} onKeyDown={composerKey} onAttach={attach} />
        </div>
      </main>
      <UploadPanel canWrite={canWrite} uploading={uploading || documentsLoading} onRefresh={() => void loadDocuments()} documents={libraryDocuments} open={uploadsOpen} inputRef={inputRef} onFiles={addFiles} onClose={() => setUploadsOpen(false)} onRemove={(id) => void removeDocument(id)} onPreview={previewDocument} />
      {source && <SourceDialog source={source} onClose={closeSource} />}
      {referenceOpen && <ReferenceDocumentDialog onClose={closeReference} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
