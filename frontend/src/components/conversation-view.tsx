"use client";

import { ArrowUpRightIcon, BookOpenTextIcon, CaretDownIcon, CheckIcon, CopyIcon, FilePdfIcon, FileTextIcon, LinkIcon, SparkleIcon, UserIcon } from "@phosphor-icons/react";
import { useState } from "react";
import type { AnswerMode, Message, Source } from "@/lib/types";

function AnswerMessage({ message, onSource, onToast }: { message: Message; onSource: (source: Source) => void; onToast: (text: string) => void }) {
  const [activeSource, setActiveSource] = useState(0);
  const [expanded, setExpanded] = useState(true);
  const [copied, setCopied] = useState(false);
  const source = message.answer.sources[activeSource];
  async function copyAnswer() {
    const answer = message.answer;
    const text = [answer.title, answer.introduction, ...answer.sections.map((section) => (section.origin === "ai_supplement" ? "【AI 补充，非文档原文】\n" : section.origin === "document" ? "【资料依据】\n" : "") + section.title + "\n" + section.content)].join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      onToast("已复制回答");
    } catch {
      onToast("无法访问剪贴板，请手动选择文字复制");
    }
  }
  function cite(index: number) {
    setActiveSource(index);
    setExpanded(true);
    requestAnimationFrame(() => document.getElementById("sources-" + message.id)?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
  }
  return (
    <article className="conversation-turn" aria-label="一轮问答">
      <div className="question-row">
        <div className="avatar user-avatar"><UserIcon size={23} weight="fill" aria-hidden="true" /></div>
        <div className="question-content"><p className="question-bubble">{message.question}</p><p className="message-time">{message.time}</p></div>
      </div>
      <div className="answer-row">
        <div className="avatar assistant-avatar"><SparkleIcon size={26} weight="fill" aria-hidden="true" /></div>
        <div className="answer-content">
          <div className="answer-paper">
            <p className="answer-origin">{message.answer.mode === "generated" ? `DeepSeek 生成回答 · ${message.answer.model}` : message.answer.mode === "no_match" ? "资料未命中 / 不足" : "原文摘录"}</p>
            <h2>{message.answer.title}</h2>
            <p className="answer-introduction">{message.answer.introduction}</p>
            <div className="answer-sections">
              {message.answer.sections.map((section, index) => (
                <section className={"answer-section" + (section.origin === "ai_supplement" ? " ai-supplement" : "")} key={index}>
                  {section.origin && <p className="section-origin">{section.origin === "ai_supplement" ? "AI 补充，非文档原文" : "资料依据"}</p>}
                  <h3>{section.title}</h3>
                  <p>{section.content} {(section.sourceIndices ?? (typeof section.sourceIndex === "number" ? [section.sourceIndex] : [])).filter((sourceIndex) => message.answer.sources[sourceIndex]).map((sourceIndex) => <button key={sourceIndex} className="citation" aria-label={"查看引用" + (sourceIndex + 1)} onClick={() => cite(sourceIndex)}>[{sourceIndex + 1}]</button>)}</p>
                </section>
              ))}
            </div>
          </div>
          <div className="answer-actions"><button className="quiet-button copy-answer" onClick={copyAnswer}>{copied ? <CheckIcon size={18} /> : <CopyIcon size={18} />}{copied ? "已复制" : "复制回答"}</button></div>
        </div>
      </div>
      {!!message.answer.sources.length && <section className="sources-area" id={"sources-" + message.id} aria-label="引用资料">
        <button className="sources-heading" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}><LinkIcon size={22} aria-hidden="true" /><span>引用资料</span><CaretDownIcon className={expanded ? "rotated" : ""} size={15} /></button>
        {expanded && <div className="source-card">
          <div className="source-card-top">
            <button className="source-file" onClick={() => onSource(source)}>{/\.pdf$/i.test(source.name) ? <FilePdfIcon size={24} weight="fill" className="pdf-color" /> : <FileTextIcon size={24} weight="fill" />}<span>{source.name}{source.page ? " · 第 " + source.page + " 页" : ""}</span><ArrowUpRightIcon size={15} className="source-open-icon" /></button>
            <span className="source-kind">{source.demo ? "演示原文" : "资料原文"}</span>
          </div>
          <p className="source-excerpt">{source.excerpt}</p>
        </div>}
      </section>}
    </article>
  );
}

type Props = {
  mode: AnswerMode;
  messages: Message[];
  busy: boolean;
  libraryName: string;
  onSource: (source: Source) => void;
  onToast: (message: string) => void;
  onSuggestion: (text: string) => void;
};

export function ConversationView(props: Props) {
  return (
    <>
      {!props.messages.length && <div className="welcome">
        <div className="welcome-icon"><BookOpenTextIcon size={38} weight="duotone" aria-hidden="true" /></div>
        <span className="eyebrow">{props.libraryName}</span>
        <h2>从一份资料，开始理解。</h2>
        <p>输入药材名称或问题，<br />在基础资料和共享文本中查找原文。</p>
        <div className="suggestions">{["陈皮的功效", "陈皮和青皮有什么区别", "帮我概括资料中的要点"].map((text) => <button onClick={() => props.onSuggestion(text)} key={text}>{text}<ArrowUpRightIcon size={17} /></button>)}</div>
        <span className="welcome-demo">{props.mode === "ai" ? "AI 优先依据资料回答；资料之外的补充会单独标注。" : "当前提供关键词原文检索，可核对完整来源。"}</span>
      </div>}
      {props.messages.map((message) => <AnswerMessage key={message.id} message={message} onSource={props.onSource} onToast={props.onToast} />)}
      {props.busy && <div className="thinking" role="status"><SparkleIcon size={20} weight="fill" aria-hidden="true" /><span>{props.mode === "ai" ? "正在检索资料并等待 DeepSeek 生成回答…" : "正在检索资料片段…"}</span></div>}
    </>
  );
}
