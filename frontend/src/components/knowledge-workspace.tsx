"use client";

import { ArrowsClockwiseIcon, ListIcon } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { initialConversations, initialDocuments, libraries } from "@/lib/demo-data";
import { createAnswer } from "@/lib/knowledge-answer";
import { generateAnswer, loadAIStatus, type AIStatus } from "@/lib/chat-api";
import { answerModeInfo, DEFAULT_ANSWER_MODE, runAnswerMode } from "@/lib/answer-mode";
import type { Conversation, DataCenterTarget, KnowledgeDocument, Source } from "@/lib/types";
import { api, errorMessage } from "@/lib/api";
import { Sidebar, type WorkspaceModule } from "./sidebar";
import { ConversationView } from "./conversation-view";
import { QuestionComposer } from "./question-composer";
import { PrescriptionDialog } from "./prescription-dialog";
import { SourceDialog } from "./source-dialog";
import { LibraryToolsDialog } from "./library-tools-dialog";
import { DataCenterDialog } from "./data-center-dialog";
import { WorkspaceModuleDialog } from "./workspace-module-dialog";
import { TestExecutionHeader, TestExecutionPage } from "./test-execution-page";
import { TestPlansPage } from "./test-plans-page";
import { NewTestTaskDialog } from "./new-test-task-dialog";
import { OperationsOverview } from "./operations-overview";
import { useDataCenterSnapshot } from "@/lib/use-data-center-snapshot";

export default function KnowledgeWorkspace() {
  const [documentError, setDocumentError] = useState("");
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsLoaded, setDocumentsLoaded] = useState(false);
  const [libraryId, setLibraryId] = useState("herbal");
  const [conversations, setConversations] = useState<Conversation[]>(initialConversations);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>(initialDocuments);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [prescriptionOpen, setPrescriptionOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const mode = DEFAULT_ANSWER_MODE;
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null);
  const [aiStatusError, setAIStatusError] = useState("");
  const [answerError, setAnswerError] = useState("");
  const [source, setSource] = useState<Source | null>(null);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [dataCenterOpen, setDataCenterOpen] = useState(false);
  const [mainPage, setMainPage] = useState<"operations" | "ai-agent">("operations");
  const [activeModule, setActiveModule] = useState<WorkspaceModule | null>(null);
  const [newTestTaskOpen, setNewTestTaskOpen] = useState(false);
  const [moduleBusy, setModuleBusy] = useState(false);
  const [dataCenterTarget, setDataCenterTarget] = useState<DataCenterTarget | undefined>();
  const snapshotReader = useDataCenterSnapshot(mainPage === "operations" || dataCenterOpen || activeModule?.id === "test-execution");
  const [referenceDocument, setReferenceDocument] = useState<Source | null>(null);
  const [toast, setToast] = useState("");
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const mainScrollRef = useRef<HTMLElement>(null);
  const pageScrollPositions = useRef({ operations: 0, "ai-agent": 0 });
  const restorePageScroll = useRef(false);
  const answerRequest = useRef<AbortController | null>(null);
  const currentLibrary = libraries.find((item) => item.id === libraryId)!;
  const currentConversation = conversations.find((item) => item.id === activeId);
  const hasAnswers = !!currentConversation?.messages.length;
  const libraryDocuments = documents.filter((item) => item.libraryId === libraryId);
  const closeSource = useCallback(() => setSource(null), []);
  const closeTools = useCallback(() => setToolsOpen(false), []);
  const closePrescription = useCallback(() => setPrescriptionOpen(false), []);
  const closeDataCenter = useCallback(() => setDataCenterOpen(false), []);
  const closeModule = useCallback(() => { setNewTestTaskOpen(false); setActiveModule(null); }, []);
  const closeNewTestTask = useCallback(() => setNewTestTaskOpen(false), []);
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
      setDocumentsLoaded(true);
    } catch (cause) { setDocumentError(errorMessage(cause)); }
    finally { setDocumentsLoading(false); }
  }, []);
  useEffect(() => {
    if (!documentsLoaded && !documentsLoading && !documentError) void loadDocuments();
  }, [documentsLoaded, documentsLoading, documentError, loadDocuments]);
  useEffect(() => {
    let active = true;
    loadAIStatus().then((status) => {
      if (!active) return;
      setAIStatus(status);
    }).catch(() => { if (active) setAIStatusError("AI 状态暂时无法读取，发送时将尝试生成回答。"); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const small = window.matchMedia("(max-width: 720px)");
    const adapt = () => {
      setMobile(small.matches);
      setNavigationOpen(false);
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
    const page = mainScrollRef.current;
    if (!page) return;
    const header = page.querySelector<HTMLElement>(".main-header");
    const footer = page.querySelector<HTMLElement>(".composer-footer");
    const updateInsets = () => {
      page.style.setProperty("--page-header-height", `${header?.getBoundingClientRect().height ?? 0}px`);
      page.style.setProperty("--page-footer-height", `${mainPage === "ai-agent" && hasAnswers ? footer?.getBoundingClientRect().height ?? 0 : 0}px`);
    };
    const observer = new ResizeObserver(updateInsets);
    if (header) observer.observe(header);
    if (footer) observer.observe(footer);
    updateInsets();
    return () => observer.disconnect();
  }, [mainPage, hasAnswers]);

  useEffect(() => {
    const page = mainScrollRef.current;
    if (!page) return;
    if (restorePageScroll.current) {
      restorePageScroll.current = false;
      page.scrollTo({ top: pageScrollPositions.current[mainPage], behavior: "instant" });
      return;
    }
    if (mainPage === "ai-agent" && currentConversation?.messages.length && !page.inert) {
      const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";
      page.scrollTo({ top: page.scrollHeight, behavior });
    }
  }, [currentConversation?.messages.length, activeId, busy, mainPage]);

  useEffect(() => {
    function escape(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape" || source || toolsOpen || prescriptionOpen || dataCenterOpen || activeModule) return;
      setNavigationOpen(false);
    }
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [source, toolsOpen, prescriptionOpen, dataCenterOpen, activeModule]);

  useEffect(() => {
    if (!navigationOpen || !mobile) return;
    const panel = document.querySelector<HTMLElement>(".sidebar");
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const visibleControls = () => Array.from(panel?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]):not([tabindex="-1"]), select:not([disabled]), [tabindex="0"]') ?? []).filter((element) => element.getClientRects().length);
    visibleControls()[0]?.focus();
    function containFocus(event: globalThis.KeyboardEvent) {
      if (event.key !== "Tab" || document.querySelector('[role="dialog"][aria-modal="true"]')) return;
      const controls = visibleControls();
      const first = controls[0], last = controls[controls.length - 1];
      if (!first) return;
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    document.addEventListener("keydown", containFocus);
    return () => { document.removeEventListener("keydown", containFocus); previous?.focus({ preventScroll: true }); };
  }, [navigationOpen, mobile]);

  function selectLibrary(id: string) {
    setLibraryId(id);
    setNavigationOpen(false);
    setToolsOpen(true);
  }
  function openModule(module: WorkspaceModule) {
    setNavigationOpen(false);
    if (module.id === "ai-agent" || module.id === "operations") {
      if (module.id !== mainPage) {
        pageScrollPositions.current[mainPage] = mainScrollRef.current?.scrollTop ?? 0;
        restorePageScroll.current = true;
      }
      setMainPage(module.id);
      setActiveModule(null);
      return;
    }
    setActiveModule(module);
  }
  function openDataCenter(target?: DataCenterTarget) {
    setNavigationOpen(false);
    setDataCenterTarget(target);
    setDataCenterOpen(true);
  }
  async function ask(question: string) {
    const text = question.trim();
    if (!text || busy || answerRequest.current) return;
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
      const message = { id: crypto.randomUUID(), question: text, ...result, showSources: true, time, answeredAt: new Date().toISOString() };
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
        requestAnimationFrame(() => composerRef.current?.focus({ preventScroll: true }));
      }
    }
  }
  function submit(event: FormEvent) { event.preventDefault(); void ask(draft); }
  function composerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void ask(draft);
    }
  }
  return (
    <div className={"workspace" + (sidebarCollapsed ? " nav-collapsed" : "")}>
      {navigationOpen && <button className="drawer-backdrop navigation-backdrop" aria-label="关闭导航遮罩" onClick={() => setNavigationOpen(false)} />}
      <Sidebar open={navigationOpen} toolsOpen={toolsOpen} dataCenterOpen={dataCenterOpen} activeModule={toolsOpen || dataCenterOpen ? null : activeModule?.id ?? mainPage} onLibrary={selectLibrary} onDataCenter={openDataCenter} onModule={openModule} onClose={() => setNavigationOpen(false)} onCollapse={() => setSidebarCollapsed(true)} />
      <main ref={mainScrollRef} className="main-panel" id="main-content" inert={!!source || toolsOpen || prescriptionOpen || dataCenterOpen || !!activeModule || (navigationOpen && mobile)}>
        <header className={"main-header" + (mainPage === "operations" ? " operations-page-header" : "")}>
          <button className={"icon-button mobile-menu" + (sidebarCollapsed ? " desktop-visible" : "")} aria-label={mobile ? "打开导航" : "展开侧栏"} aria-expanded={mobile ? navigationOpen : !sidebarCollapsed} onClick={() => mobile ? setNavigationOpen(true) : setSidebarCollapsed(false)}><ListIcon size={25} /></button>
          <div className="header-context">
            <div className="breadcrumb"><h1>{mainPage === "operations" ? "运行总览" : currentLibrary.name}</h1><span className="demo-label">{mainPage === "operations" ? "煎药流程仿真" : answerModeInfo[mode].label}</span></div>
            <p>{answerModeInfo[mode].description}</p>
          </div>
          {mainPage === "operations" && <button className="ops-button operations-page-refresh" aria-label="刷新运行总览" disabled={snapshotReader.busy} onClick={snapshotReader.refreshData}><ArrowsClockwiseIcon size={18} aria-hidden="true" />{snapshotReader.busy ? "读取中" : "刷新"}</button>}
        </header>
        {mainPage === "operations" && <section className="workspace-page workspace-operations" aria-label="运行总览内容"><OperationsOverview state={snapshotReader.state} /></section>}
        <div className="workspace-page" hidden={mainPage !== "ai-agent"}>
          {(documentsLoading || documentError) && <div className="document-feedback" role={documentError ? "alert" : "status"}><span>{documentError || "正在读取知识库资料…"}</span>{documentError && <button onClick={() => void loadDocuments()}>重新读取</button>}</div>}
          <div className={"chat-body" + (!(currentConversation?.messages.length) ? " welcome-state" : "")}>
            <div className="conversation-scroll" aria-label="问答内容" aria-busy={busy}>
              <ConversationView mode={mode} messages={currentConversation?.messages ?? []} busy={busy} libraryName={currentLibrary.name} onSource={setSource} onToast={setToast} onDataCenter={openDataCenter} />
            </div>
            <QuestionComposer draft={draft} busy={busy} disabled={false} prescriptionOpen={prescriptionOpen} error={answerError} status={aiStatus} statusError={aiStatusError} inputRef={composerRef} onDraft={setDraft} onSubmit={submit} onKeyDown={composerKey} onPrescription={() => setPrescriptionOpen(true)} />
          </div>
        </div>
      </main>
      {source && <SourceDialog source={source} onClose={closeSource} />}
      {toolsOpen && <LibraryToolsDialog onClose={closeTools} />}
      {prescriptionOpen && <PrescriptionDialog onClose={closePrescription} />}
      {dataCenterOpen && <DataCenterDialog initialTarget={dataCenterTarget} snapshotReader={snapshotReader} onClose={closeDataCenter} />}
      {activeModule && <WorkspaceModuleDialog title={activeModule.label} onClose={closeModule} busy={moduleBusy} className={activeModule.id === "test-execution" ? "test-execution-dialog" : undefined} headerContent={activeModule.id === "test-execution" ? <TestExecutionHeader onNewTask={() => setNewTestTaskOpen(true)} newTaskOpen={newTestTaskOpen} /> : undefined}>{activeModule.id === "test-execution" ? <TestExecutionPage snapshotReader={snapshotReader} /> : activeModule.id === "test-plans" ? <TestPlansPage onBusyChange={setModuleBusy} onSaved={snapshotReader.refreshData} /> : undefined}</WorkspaceModuleDialog>}
      {newTestTaskOpen && <NewTestTaskDialog onClose={closeNewTestTask} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
