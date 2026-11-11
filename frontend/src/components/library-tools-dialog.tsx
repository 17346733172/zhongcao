"use client";

import { BookOpenTextIcon, CheckCircleIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ReferenceDocumentDialog } from "./reference-document-dialog";
import { PrescriptionDialog } from "./prescription-dialog";

type Tab = "reference" | "prescription";
const tabs = [
  { id: "reference", label: "基础资料", Icon: BookOpenTextIcon },
  { id: "prescription", label: "处方检查", Icon: CheckCircleIcon },
] as const;

export function LibraryToolsDialog({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("reference");
  const [prescriptionVisited, setPrescriptionVisited] = useState(false);
  const dialog = useRef<HTMLElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const previous = useRef<HTMLElement | null>(null);
  useEffect(() => {
    previous.current ??= document.activeElement instanceof HTMLElement ? document.activeElement : null;
    close.current?.focus();
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") { event.preventDefault(); onClose(); return; }
      if (event.key !== "Tab") return;
      const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]):not([tabindex="-1"]),textarea:not([disabled]),select:not([disabled]),summary,[tabindex="0"]') ?? []).filter(element => element.getClientRects().length);
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      requestAnimationFrame(() => {
        if (dialog.current?.isConnected) return;
        const mobileMenu = document.querySelector<HTMLElement>('.mobile-menu[aria-label="打开导航"]');
        const target = mobileMenu?.getClientRects().length ? mobileMenu : previous.current;
        target?.focus();
      });
    };
  }, [onClose]);

  function selectTab(id: Tab) {
    if (id === "prescription") setPrescriptionVisited(true);
    setTab(id);
  }
  function tabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number;
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") next = 1 - index;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    selectTab(tabs[next].id);
    dialog.current?.querySelector<HTMLElement>(`#library-tools-tab-${tabs[next].id}`)?.focus();
  }

  return <div className="modal-backdrop library-tools-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section ref={dialog} className="library-tools-dialog" role="dialog" aria-modal="true" aria-labelledby="library-tools-title">
      <header className="library-tools-header">
        <h2 id="library-tools-title">中药资料与处方</h2>
        <button ref={close} className="icon-button" aria-label="关闭中药资料与处方" onClick={onClose}><XIcon size={22} /></button>
      </header>
      <div className="library-tools-tabs" role="tablist" aria-label="中药工具">
        {tabs.map(({ id, label, Icon }, index) => <button key={id} id={`library-tools-tab-${id}`} role="tab" aria-selected={tab === id} aria-controls={`library-tools-panel-${id}`} tabIndex={tab === id ? 0 : -1} onClick={() => selectTab(id)} onKeyDown={event => tabKey(event, index)}><Icon size={20} aria-hidden="true" />{label}</button>)}
      </div>
      <div className="library-tools-panel" id="library-tools-panel-reference" role="tabpanel" aria-labelledby="library-tools-tab-reference" hidden={tab !== "reference"}>
        <ReferenceDocumentDialog embedded onClose={onClose} />
      </div>
      <div className="library-tools-panel" id="library-tools-panel-prescription" role="tabpanel" aria-labelledby="library-tools-tab-prescription" hidden={tab !== "prescription"}>
        {prescriptionVisited && <PrescriptionDialog embedded active={tab === "prescription"} onClose={onClose} />}
      </div>
    </section>
  </div>;
}
