"use client";

import { ArrowUpIcon, BookOpenTextIcon, PaperclipIcon, SparkleIcon } from "@phosphor-icons/react";
import type { FormEvent, KeyboardEvent, RefObject } from "react";
import type { AIStatus } from "@/lib/chat-api";
import { answerModeInfo, isAnswerOptionSelected } from "@/lib/answer-mode";
import type { AnswerMode, AnswerOption } from "@/lib/types";

type Props = {
  draft: string; mode: AnswerMode; busy: boolean; disabled: boolean;
  canWrite: boolean; uploading: boolean; error: string;
  status: AIStatus | null; statusError: string;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  onDraft: (value: string) => void; onMode: (option: AnswerOption) => void;
  onSubmit: (event: FormEvent) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onAttach: () => void;
};

export function QuestionComposer(props: Props) {
  return (
    <footer className="composer-footer">
      {props.error && <p className="answer-error" role="alert">{props.error}</p>}
      <form className="composer" onSubmit={props.onSubmit}>
        <label className="visually-hidden" htmlFor="question">向中药资料提问</label>
        <textarea id="question" ref={props.inputRef} rows={2} maxLength={2000} value={props.draft} onChange={(event) => props.onDraft(event.target.value)} onKeyDown={props.onKeyDown} placeholder="给本草知问发送消息" disabled={props.busy || props.disabled} />
        <div className="composer-tools">
          <div className="answer-mode-switch" role="group" aria-label="回答方式，可多选" aria-describedby="answer-mode-help">
            <button type="button" aria-pressed={isAnswerOptionSelected(props.mode, "ai")} disabled={props.busy || !props.status?.configured} onClick={() => props.onMode("ai")}><SparkleIcon size={17} aria-hidden="true" />AI 回答</button>
            <button type="button" aria-pressed={isAnswerOptionSelected(props.mode, "extract")} disabled={props.busy} onClick={() => props.onMode("extract")}><BookOpenTextIcon size={17} aria-hidden="true" />原文检索</button>
          </div>
          <div className="composer-actions">
            {props.canWrite && <button type="button" disabled={props.uploading || props.disabled} className="icon-button attach-button" aria-label="添加资料附件" onClick={props.onAttach}><PaperclipIcon size={23} /></button>}
            <button className="send-button primary-button" type="submit" aria-label={props.busy ? "正在生成回答" : "发送"} disabled={!props.draft.trim() || props.busy || props.disabled || props.mode === "none"}><ArrowUpIcon size={25} weight="bold" aria-hidden="true" /></button>
          </div>
        </div>
      </form>
      <div className="composer-meta">
        <p id="answer-mode-help" aria-live="polite">{answerModeInfo[props.mode].note}</p>
        <span className="ai-status-note">{props.statusError || (props.status ? props.status.configured ? "DeepSeek 已配置" : "AI 服务尚未配置，可先使用原文检索。" : "正在检查 AI 服务…")}</span>
      </div>
    </footer>
  );
}
