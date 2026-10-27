"use client";

import { DownloadSimpleIcon, FileTextIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";
import type { Source } from "@/lib/types";
import { DocumentContent } from "./document-content";

type Props = {
  source: Source;
  onClose: () => void;
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
};

export function SourceDialog({ source, onClose, loading = false, error, onRetry }: Props) {
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const hasContent = !loading && !error && source.fullText.trim().length > 0;
  const chapters = source.blocks?.flatMap((block, index) => block.type === "heading" && block.level === 1 ? [{ index, text: block.text }] : []) ?? [];
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    close.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const focusable = dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]), [href], select:not([disabled]), textarea, [tabindex="0"]');
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
        <div className="source-dialog-meta"><span>{loading ? "正在读取文档" : error ? "文档读取失败" : !hasContent ? "待接入文档" : source.demo ? "演示原文" : "资料原文"}</span>{source.page && <span>引用位置：第 {source.page} 页（示例）</span>}</div>
        {hasContent && (chapters.length > 0 || source.downloadUrl) && <div className="source-dialog-tools">
          {chapters.length > 0 && <label className="source-chapter-picker">定位章节<select defaultValue="" onChange={(event) => content.current?.querySelector(`#document-section-${event.target.value}`)?.scrollIntoView({ block: "start" })}>
            <option value="" disabled>选择章节</option>
            {chapters.map((chapter) => <option key={chapter.index} value={chapter.index}>{chapter.text}</option>)}
          </select></label>}
          {source.downloadUrl && <a className="source-download" href={source.downloadUrl} download={source.name}><DownloadSimpleIcon size={18} aria-hidden="true" />下载 Word 原文</a>}
        </div>}
        {loading ? <div className="source-empty" role="status"><FileTextIcon size={38} aria-hidden="true" /><p>正在读取中药基础知识…</p></div> : error ? <div className="source-empty" role="alert"><h3>文档暂时无法打开</h3><p>{error}</p>{onRetry && <button className="source-retry primary-button" onClick={() => { close.current?.focus(); onRetry(); }}>重新读取</button>}</div> : hasContent ? <div ref={content} className={"original-content" + (source.blocks ? " rich-document" : "")} tabIndex={0}>{source.blocks ? <DocumentContent blocks={source.blocks} /> : source.fullText}</div> : (
          <div className="source-empty">
            <FileTextIcon size={38} aria-hidden="true" />
            <h3>文档待提供</h3>
            <p>中药材相关文档尚未接入，提供正式文档后将在这里展示。</p>
          </div>
        )}
        <footer>{loading ? "正在加载文档正文。" : error ? "可重新读取文档，或关闭窗口稍后再试。" : hasContent ? "引用内容用于资料核对，请以真实文献为准。" : "正式文档接入后，可在此阅读完整内容。"}</footer>
      </div>
    </div>
  );
}
