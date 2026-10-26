"use client";

import { InfoIcon, ListIcon, PaperclipIcon, UploadSimpleIcon } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { createAnswer, initialConversations, initialDocuments, libraries } from "@/lib/demo-data";
import type { Conversation, KnowledgeDocument, Source } from "@/lib/types";
import { Sidebar } from "./sidebar";
import { ConversationView } from "./conversation-view";
import { UploadPanel } from "./upload-panel";
import { SourceDialog } from "./source-dialog";

export default function KnowledgeWorkspace() {
  const [libraryId, setLibraryId] = useState("herbal");
  const [conversations, setConversations] = useState<Conversation[]>(initialConversations);
  const [activeId, setActiveId] = useState<string | null>("chenpi");
  const [documents, setDocuments] = useState<KnowledgeDocument[]>(initialDocuments);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [uploadsOpen, setUploadsOpen] = useState(true);
  const [compact, setCompact] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [source, setSource] = useState<Source | null>(null);
  const [toast, setToast] = useState("");
  const [clock, setClock] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const responseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queueReady = useRef(false);
  const currentLibrary = libraries.find((item) => item.id === libraryId)!;
  const currentConversation = conversations.find((item) => item.id === activeId);
  const libraryDocuments = documents.filter((item) => item.libraryId === libraryId);
  const closeSource = useCallback(() => setSource(null), []);

  useEffect(() => {
    const media = window.matchMedia("(max-width: 1100px)");
    const small = window.matchMedia("(max-width: 720px)");
    const adapt = () => {
      setCompact(media.matches);
      setMobile(small.matches);
      if (media.matches) setUploadsOpen(false);
    };
    adapt();
    media.addEventListener("change", adapt);
    small.addEventListener("change", adapt);
    const initialDelay = setTimeout(() => { queueReady.current = true; }, 10000);
    const ticker = setInterval(() => {
      if (!queueReady.current) return;
      setDocuments((current) => {
        const item = current.find((doc) => doc.status === "parsing") ?? current.find((doc) => doc.status === "queued");
        if (!item) return current;
        return current.map((doc) => {
          if (doc.id !== item.id) return doc;
          if (doc.status === "queued") return { ...doc, status: "parsing", progress: 12 };
          const progress = Math.min(100, doc.progress + 16);
          if (progress < 100) return { ...doc, progress };
          return { ...doc, progress: 100, status: doc.content.trim() ? "ready" : "needs-parser" };
        });
      });
    }, 700);
    const updateClock = () => {
      const date = new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
      setClock(date + " · 上海时间");
    };
    updateClock();
    const clockTimer = setInterval(updateClock, 60000);
    return () => {
      media.removeEventListener("change", adapt);
      small.removeEventListener("change", adapt);
      clearTimeout(initialDelay);
      clearInterval(ticker);
      clearInterval(clockTimer);
      if (responseTimer.current) clearTimeout(responseTimer.current);
    };
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
      if (event.key !== "Escape" || source) return;
      setNavigationOpen(false);
      if (window.matchMedia("(max-width: 1100px)").matches) setUploadsOpen(false);
    }
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [source]);

  useEffect(() => {
    const selector = navigationOpen && mobile ? ".sidebar" : uploadsOpen && compact ? ".upload-panel" : null;
    if (!selector || source) return;
    const panel = document.querySelector<HTMLElement>(selector);
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const visibleControls = () => Array.from(panel?.querySelectorAll<HTMLElement>('button:not([disabled]), [tabindex="0"]') ?? []).filter((element) => element.getClientRects().length);
    visibleControls()[0]?.focus();
    function containFocus(event: globalThis.KeyboardEvent) {
      if (event.key !== "Tab") return;
      const controls = visibleControls();
      const first = controls[0], last = controls[controls.length - 1];
      if (!first) return;
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", containFocus);
    return () => { document.removeEventListener("keydown", containFocus); previous?.focus(); };
  }, [navigationOpen, uploadsOpen, compact, mobile, source]);

  function cancelPending() {
    if (responseTimer.current) clearTimeout(responseTimer.current);
    responseTimer.current = null;
    setBusy(false);
  }
  function newConversation() {
    cancelPending();
    setActiveId(null);
    setDraft("");
    setNavigationOpen(false);
    requestAnimationFrame(() => composerRef.current?.focus());
  }
  function selectLibrary(id: string) {
    cancelPending();
    setLibraryId(id);
    setActiveId(null);
    setDraft("");
    setNavigationOpen(false);
  }
  function selectConversation(id: string) {
    cancelPending();
    setActiveId(id);
    setDraft("");
    setNavigationOpen(false);
  }
  function ask(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    setBusy(true);
    setDraft("");
    const conversationId = activeId ?? crypto.randomUUID();
    const answer = createAnswer(text, libraryDocuments);
    const time = "今天 " + new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
    responseTimer.current = setTimeout(() => {
      const message = { id: crypto.randomUUID(), question: text, answer, time };
      setConversations((current) => {
        const exists = current.find((item) => item.id === conversationId);
        if (exists) return current.map((item) => item.id === conversationId ? { ...item, messages: [...item.messages, message] } : item);
        return [{ id: conversationId, libraryId, title: text.slice(0, 16), messages: [message] }, ...current];
      });
      setActiveId(conversationId);
      setBusy(false);
      responseTimer.current = null;
      requestAnimationFrame(() => composerRef.current?.focus());
    }, 650);
  }
  function submit(event: FormEvent) { event.preventDefault(); ask(draft); }
  function composerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      ask(draft);
    }
  }
  async function addFiles(files: File[]) {
    if (!files.length) return;
    setUploadsOpen(true);
    queueReady.current = true;
    const entries = await Promise.all(files.map(async (file): Promise<KnowledgeDocument> => {
      const base: KnowledgeDocument = { id: crypto.randomUUID(), libraryId, name: file.name, status: "queued", progress: 0, content: "", demo: false };
      if (!/\.(md|txt|pdf|docx)$/i.test(file.name)) return { ...base, status: "error", error: "格式不支持，请选择 MD、TXT、PDF 或 Word" };
      if (file.size > 10 * 1024 * 1024) return { ...base, status: "error", error: "文件超过本地演示的 10 MB 限制" };
      if (!/\.(md|txt)$/i.test(file.name)) return base;
      try {
        const content = (await file.text()).replace(/^\uFEFF/, "");
        return content.trim() ? { ...base, content } : { ...base, status: "error", error: "资料内容为空" };
      } catch {
        return { ...base, status: "error", error: "文件读取失败，请重新选择" };
      }
    }));
    setDocuments((current) => [...current, ...entries]);
    setToast("已加入当前知识库的本地处理队列");
  }
  function previewDocument(doc: KnowledgeDocument) {
    setSource({ id: doc.id, name: doc.name, excerpt: doc.content.slice(0, 300), fullText: doc.content, demo: doc.demo });
  }
  function attach() {
    setUploadsOpen(true);
    inputRef.current?.click();
  }

  return (
    <div className={"workspace" + (!uploadsOpen ? " uploads-hidden" : "")}>
      {navigationOpen && <button className="drawer-backdrop navigation-backdrop" aria-label="关闭导航遮罩" onClick={() => setNavigationOpen(false)} />}
      {uploadsOpen && <button className="drawer-backdrop upload-backdrop" aria-label="关闭上传遮罩" onClick={() => setUploadsOpen(false)} />}
      <Sidebar libraryId={libraryId} activeId={activeId} conversations={conversations} open={navigationOpen} onLibrary={selectLibrary} onConversation={selectConversation} onNew={newConversation} onClose={() => setNavigationOpen(false)} />
      <main className="main-panel" id="main-content" inert={!!source || (navigationOpen && mobile) || (uploadsOpen && compact)}>
        <header className="main-header">
          <button className="icon-button mobile-menu" aria-label="打开导航" aria-expanded={navigationOpen} onClick={() => setNavigationOpen(true)}><ListIcon size={25} /></button>
          <div className="header-context">
            <div className="breadcrumb"><span className="breadcrumb-root">知识库<span className="breadcrumb-slash">/</span></span><h1>{currentLibrary.name}</h1><span className="demo-label">演示资料</span></div>
            <p>从你上传的资料中查找答案</p>
          </div>
          <button className="upload-trigger" aria-label="上传资料" onClick={() => setUploadsOpen(true)} aria-expanded={uploadsOpen}><UploadSimpleIcon size={22} aria-hidden="true" /><span>上传资料</span></button>
        </header>
        <div ref={scrollRef} className="conversation-scroll" aria-label="问答内容" aria-busy={busy}>
          <ConversationView messages={currentConversation?.messages ?? []} busy={busy} libraryName={currentLibrary.name} onSource={setSource} onToast={setToast} onSuggestion={ask} />
        </div>
        <footer className="composer-footer">
          <form className="composer" onSubmit={submit}>
            <button type="button" className="icon-button attach-button" aria-label="添加资料附件" onClick={attach}><PaperclipIcon size={22} /></button>
            <label className="visually-hidden" htmlFor="question">向中药资料提问</label>
            <textarea id="question" ref={composerRef} rows={1} maxLength={2000} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={composerKey} placeholder="向中药资料提问…" disabled={busy} />
            <button className="send-button primary-button" type="submit" disabled={!draft.trim() || busy}>{busy ? "整理中" : "发送"}</button>
          </form>
          <div className="composer-meta"><p><InfoIcon size={16} aria-hidden="true" /><span>前端演示 · 请核对引用原文</span></p><time>{clock}</time></div>
        </footer>
      </main>
      <UploadPanel documents={libraryDocuments} open={uploadsOpen} inputRef={inputRef} onFiles={addFiles} onClose={() => setUploadsOpen(false)} onRemove={(id) => setDocuments((current) => current.filter((doc) => doc.id !== id))} onPreview={previewDocument} />
      {source && <SourceDialog source={source} onClose={closeSource} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
