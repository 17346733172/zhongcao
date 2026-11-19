"use client";

import { FileTextIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, type ReactNode } from "react";

export function WorkspaceModuleDialog({ title, onClose, children, className, headerContent, busy = false }: { title: string; onClose: () => void; children?: ReactNode; className?: string; headerContent?: ReactNode; busy?: boolean }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const previous = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    previous.current ??= document.activeElement instanceof HTMLElement ? document.activeElement : null;
    element.showModal();
    return () => {
      element.close();
      requestAnimationFrame(() => {
        if (element.isConnected) return;
        const mobileMenu = document.querySelector<HTMLElement>('.mobile-menu[aria-label="打开导航"]');
        const target = mobileMenu?.getClientRects().length ? mobileMenu : previous.current;
        target?.focus({ preventScroll: true });
      });
    };
  }, []);

  return <dialog ref={dialog} className={"source-dialog workspace-module-dialog" + (className ? ` ${className}` : children ? " operations-overview-dialog" : "")} aria-labelledby="workspace-module-title" aria-busy={busy} aria-describedby={children ? undefined : "workspace-module-description"} onCancel={event => { event.preventDefault(); if (!busy) onClose(); }} onKeyDown={event => {
    if (event.key !== "Tab") return;
    const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),[tabindex="0"]')).filter(element => element.getClientRects().length);
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }} onClick={event => {
    if (busy || event.target !== event.currentTarget) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
  }}>
    <header>
      {headerContent ?? <h2 id="workspace-module-title">{title}</h2>}
      <button autoFocus className="icon-button" aria-label={`关闭${title}`} disabled={busy} onClick={onClose}><XIcon size={22} /></button>
    </header>
    {children ?? <div className="workspace-module-empty">
      <FileTextIcon size={40} weight="light" aria-hidden="true" />
      <h3>内容待补充</h3>
      <p id="workspace-module-description">{title}的内容将在提供后补充。</p>
    </div>}
  </dialog>;
}
