"use client";

import { CheckCircleIcon, ClockIcon, FileIcon, FilePdfIcon, FileTextIcon, InfoIcon, UploadSimpleIcon, WarningCircleIcon, XIcon } from "@phosphor-icons/react";
import { useState, type ChangeEvent, type DragEvent, type RefObject } from "react";
import type { KnowledgeDocument } from "@/lib/types";

type Props = {
  documents: KnowledgeDocument[];
  open: boolean;
  inputRef: RefObject<HTMLInputElement | null>;
  onFiles: (files: File[]) => void;
  onClose: () => void;
  onRemove: (id: string) => void;
  onPreview: (doc: KnowledgeDocument) => void;
};

export function UploadPanel({ documents, open, inputRef, onFiles, onClose, onRemove, onPreview }: Props) {
  const [dragging, setDragging] = useState(false);
  function changed(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files) onFiles(Array.from(event.target.files));
    event.target.value = "";
  }
  function dropped(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    onFiles(Array.from(event.dataTransfer.files));
  }
  return (
    <aside className={"upload-panel" + (open ? " panel-open" : "")} aria-label="资料上传">
      <div className="upload-heading"><h2>资料上传</h2><button className="icon-button" aria-label="关闭上传面板" onClick={onClose}><XIcon size={19} /></button></div>
      <input ref={inputRef} className="visually-hidden" type="file" accept=".md,.txt,.pdf,.docx" multiple onChange={changed} aria-label="选择知识库资料" tabIndex={-1} />
      <button className={"drop-zone" + (dragging ? " is-dragging" : "")} onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={dropped}>
        <FileIcon size={36} weight="light" aria-hidden="true" />
        <span>拖入文件，或<span className="link-color">点击选择</span></span>
        <span className="drop-hint">Markdown、TXT、PDF、Word</span>
      </button>
      <p className="upload-capability">MD / TXT 本地读取 · PDF / Word 待接入解析</p>
      <div className="upload-list" aria-live="polite" aria-relevant="additions removals">
        {documents.map((doc) => (
          <div className="upload-item" key={doc.id}>
            <div className={"file-symbol " + (/\.pdf$/i.test(doc.name) ? "pdf-symbol" : "text-symbol")}>
              {/\.pdf$/i.test(doc.name) ? <FilePdfIcon size={31} weight="fill" aria-hidden="true" /> : <FileTextIcon size={31} weight="fill" aria-hidden="true" />}
            </div>
            <div className="upload-info">
              <button className="file-title" title={doc.name} disabled={!doc.content} onClick={() => onPreview(doc)}>{doc.name}</button>
              {doc.status === "parsing" && <>
                <p className="file-status parsing">{doc.demo ? "演示解析中" : "本地读取中"} <span>{doc.progress}%</span></p>
                <progress aria-label={doc.name + "处理进度"} max={100} value={doc.progress} />
              </>}
              {doc.status === "ready" && <p className="file-status ready"><CheckCircleIcon size={17} weight="fill" aria-hidden="true" />{doc.demo ? "已就绪 · 示例" : "已就绪 · 本地"}</p>}
              {doc.status === "queued" && <p className="file-status"><ClockIcon size={17} aria-hidden="true" />等待处理</p>}
              {doc.status === "needs-parser" && <p className="file-status pending-parser"><InfoIcon size={17} aria-hidden="true" />待接入解析服务</p>}
              {doc.status === "error" && <p className="file-status upload-error"><WarningCircleIcon size={17} aria-hidden="true" />{doc.error || "读取失败，请重新选择"}</p>}
            </div>
            <button className="icon-button remove-file" aria-label={"移除" + doc.name} onClick={() => onRemove(doc.id)}><XIcon size={16} /></button>
          </div>
        ))}
        {!documents.length && <div className="empty-uploads"><UploadSimpleIcon size={29} aria-hidden="true" /><p>把第一份资料放进来</p><span>资料会归入当前知识库</span></div>}
      </div>
      <div className="upload-note"><InfoIcon size={19} aria-hidden="true" /><p>读取完成后可查看原文</p></div>
      <p className="privacy-note">文件仅在当前页面中处理，不会上传到服务器。刷新页面后清除。</p>
    </aside>
  );
}
