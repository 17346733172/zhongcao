"use client";

import { FileTextIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";
import type { Source } from "@/lib/types";

export function SourceDialog({ source, onClose }: { source: Source; onClose: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    close.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const focusable = dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], textarea, [tabindex="0"]');
        if (!focusable?.length) return;
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    }
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); previous?.focus(); };
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="source-dialog-title" className="source-dialog" onClick={(event) => event.stopPropagation()}>
        <header><div><FileTextIcon size={24} /><h2 id="source-dialog-title">{source.name}</h2></div><button ref={close} className="icon-button" aria-label="关闭原文" onClick={onClose}><XIcon size={22} /></button></header>
        <div className="source-dialog-meta"><span>{source.demo ? "演示原文" : "本地读取原文"}</span>{source.page && <span>引用位置：第 {source.page} 页（示例）</span>}</div>
        <div className="original-content" tabIndex={0}>{source.fullText}</div>
        <footer>引用内容用于资料核对，请以真实文献为准。</footer>
      </div>
    </div>
  );
}
