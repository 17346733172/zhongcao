"use client";

import { XIcon } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";
import { ReferenceDocumentDialog } from "./reference-document-dialog";

export function LibraryToolsDialog({ onClose }: { onClose: () => void }) {
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
        target?.focus({ preventScroll: true });
      });
    };
  }, [onClose]);

  return <div className="modal-backdrop library-tools-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section ref={dialog} className="library-tools-dialog" role="dialog" aria-modal="true" aria-labelledby="library-tools-title">
      <header className="library-tools-header">
        <h2 id="library-tools-title">中药基础资料</h2>
        <button ref={close} className="icon-button" aria-label="关闭中药基础资料" onClick={onClose}><XIcon size={22} /></button>
      </header>
      <div className="library-tools-panel">
        <ReferenceDocumentDialog embedded onClose={onClose} />
      </div>
    </section>
  </div>;
}
