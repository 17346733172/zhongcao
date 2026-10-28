"use client";
import { CheckCircleIcon, ClockIcon, FileIcon, FilePdfIcon, FileTextIcon, InfoIcon, UploadSimpleIcon, WarningCircleIcon, XIcon } from "@phosphor-icons/react";
import { useState, type ChangeEvent, type DragEvent, type RefObject } from "react";
import type { KnowledgeDocument } from "@/lib/types";
type Props = {
  documents: KnowledgeDocument[]; open: boolean; canWrite: boolean; uploading: boolean;
  inputRef: RefObject<HTMLInputElement | null>;
  onFiles: (files: File[]) => void; onClose: () => void; onRemove: (id: string) => void;
  onPreview: (doc: KnowledgeDocument) => void; onRefresh: () => void;
};
export function UploadPanel({ documents, open, canWrite, uploading, inputRef, onFiles, onClose, onRemove, onPreview, onRefresh }: Props) {
  const [dragging, setDragging] = useState(false);
  function changed(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files && canWrite && !uploading) onFiles(Array.from(event.target.files));
    event.target.value = "";
  }
  function dropped(event: DragEvent<HTMLButtonElement>) { event.preventDefault(); setDragging(false); if (canWrite && !uploading) onFiles(Array.from(event.dataTransfer.files)); }
  return (
    <aside role="dialog" aria-modal="true" className={"upload-panel" + (open ? " panel-open" : "")} aria-label={canWrite ? "资料上传" : "知识库资料"}>
      <div className="upload-heading"><h2>{canWrite ? "资料上传" : "知识库资料"}</h2><button className="icon-button" aria-label="关闭上传面板" onClick={onClose}><XIcon size={19} /></button></div>
      {canWrite ? <><input ref={inputRef} className="visually-hidden" type="file" accept=".md,.txt,.pdf,.docx" multiple onChange={changed} aria-label="选择知识库资料" tabIndex={-1} disabled={uploading} />
        <button disabled={uploading} className={"drop-zone" + (dragging ? " is-dragging" : "")} onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); if (!uploading) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={dropped}><FileIcon size={36} weight="light" aria-hidden="true" /><span>{uploading ? "正在处理资料…" : <>拖入文件，或<span className="link-color">点击选择</span></>}</span><span className="drop-hint">Markdown / TXT · 单个文件最多 10 MB</span></button>
        <p className="upload-capability">MD / TXT 保存到服务器 · PDF / Word 待接入解析</p></> : <p className="readonly-note"><InfoIcon size={20} aria-hidden="true" />当前为普通用户，可查看资料和提问。添加或移除资料请联系编辑员或管理员。</p>}
      <button className="quiet-button" disabled={uploading} onClick={onRefresh}>刷新共享资料</button>
      <div className="upload-list" aria-live="polite" aria-relevant="additions removals">
        {documents.map((doc) => <div className="upload-item" key={doc.id}>
          <div className={"file-symbol " + (/\.pdf$/i.test(doc.name) ? "pdf-symbol" : "text-symbol")}>{/\.pdf$/i.test(doc.name) ? <FilePdfIcon size={31} weight="fill" aria-hidden="true" /> : <FileTextIcon size={31} weight="fill" aria-hidden="true" />}</div>
          <div className="upload-info"><button className="file-title" title={doc.name} disabled={!doc.content} onClick={() => onPreview(doc)}>{doc.name}</button>
            {doc.status === "parsing" && <><p className="file-status parsing">{doc.demo ? "演示解析中" : "正在保存"}{doc.demo && <span>{doc.progress}%</span>}</p>{doc.demo && <progress aria-label={doc.name + "处理进度"} max={100} value={doc.progress} />}</>}
            {doc.status === "ready" && <p className="file-status ready"><CheckCircleIcon size={17} weight="fill" aria-hidden="true" />{doc.demo ? "已就绪 · 示例" : doc.stored ? "已保存 · 共享" : "已就绪 · 本地"}</p>}
            {doc.status === "queued" && <p className="file-status"><ClockIcon size={17} aria-hidden="true" />等待处理</p>}
            {doc.status === "needs-parser" && <p className="file-status pending-parser"><InfoIcon size={17} aria-hidden="true" />未上传 · 待接入解析服务</p>}
            {doc.status === "error" && <p className="file-status upload-error"><WarningCircleIcon size={17} aria-hidden="true" />{doc.error || "读取失败，请重新选择"}</p>}
          </div>{canWrite && <button className="icon-button remove-file" disabled={uploading} aria-label={"移除" + doc.name} onClick={() => onRemove(doc.id)}><XIcon size={16} /></button>}
        </div>)}
        {!documents.length && <div className="empty-uploads"><UploadSimpleIcon size={29} aria-hidden="true" /><p>暂无共享文本资料</p><span>{canWrite ? "添加第一份文本资料" : "等待编辑员添加资料"}</span></div>}
      </div>
      <div className="upload-note"><InfoIcon size={19} aria-hidden="true" /><p>点击资料名称可查看原文</p></div><p className="privacy-note">已保存文本供本系统所有登录用户查看。示例有单独标识；PDF / Word 尚不上传。支持原文检索；AI 回答需配置服务，对话仅本次保留。</p>
    </aside>
  );
}
