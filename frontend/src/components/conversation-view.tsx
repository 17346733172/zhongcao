"use client";

import { ArrowUpRightIcon, BookOpenTextIcon, CaretDownIcon, CheckIcon, CopyIcon, FilePdfIcon, FileTextIcon, LinkIcon, SparkleIcon, UserIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { answerModeInfo } from "@/lib/answer-mode";
import type { Answer, AnswerMode, Message, Source } from "@/lib/types";

type AnswerActions = { onSource: (source: Source) => void; onToast: (text: string) => void };

function AnswerResult({ answer, id, label, onSource, onToast }: AnswerActions & { answer: Answer; id: string; label: string }) {
  const [activeSource, setActiveSource] = useState(0);
  const [expanded, setExpanded] = useState(true);
  const [copied, setCopied] = useState(false);
  const source = answer.sources[activeSource];
  async function copyAnswer() {
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
    requestAnimationFrame(() => document.getElementById("sources-" + id)?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
  }
  return (
      <section className="answer-row" aria-label={label}>
        <div className="avatar assistant-avatar"><SparkleIcon size={26} weight="fill" aria-hidden="true" /></div>
        <div className="answer-content">
          <div className="answer-paper">
            <p className="answer-origin">{answer.mode === "generated" ? `DeepSeek 生成回答 · ${answer.model}` : answer.mode === "clarification" ? "需要补充问题" : answer.mode === "no_match" ? "资料未命中 / 不足" : "原文摘录"}</p>
            <h2>{answer.title}</h2>
            <p className="answer-introduction">{answer.introduction}</p>
            <div className="answer-sections">
              {answer.sections.map((section, index) => (
                <section className={"answer-section" + (section.origin === "ai_supplement" ? " ai-supplement" : "")} key={index}>
                  {section.origin && <p className="section-origin">{section.origin === "ai_supplement" ? "AI 补充，非文档原文" : "资料依据"}</p>}
                  <h3>{section.title}</h3>
                  <p>{section.content} {(section.sourceIndices ?? (typeof section.sourceIndex === "number" ? [section.sourceIndex] : [])).filter((sourceIndex) => answer.sources[sourceIndex]).map((sourceIndex) => <button key={sourceIndex} className="citation" aria-label={"查看引用" + (sourceIndex + 1)} onClick={() => cite(sourceIndex)}>[{sourceIndex + 1}]</button>)}</p>
                </section>
              ))}
            </div>
          </div>
          <div className="answer-actions"><button className="quiet-button copy-answer" onClick={copyAnswer}>{copied ? <CheckIcon size={18} /> : <CopyIcon size={18} />}{copied ? "已复制" : "复制回答"}</button></div>
          {!!answer.sources.length && <section className="sources-area" id={"sources-" + id} aria-label="引用资料">
            <button className="sources-heading" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}><LinkIcon size={22} aria-hidden="true" /><span>引用资料</span><CaretDownIcon className={expanded ? "rotated" : ""} size={15} /></button>
            {expanded && <div className="source-card">
              <div className="source-card-top">
                <button className="source-file" onClick={() => onSource(source)}>{/\.pdf$/i.test(source.name) ? <FilePdfIcon size={24} weight="fill" className="pdf-color" /> : <FileTextIcon size={24} weight="fill" />}<span>{source.name}{source.page ? " · 第 " + source.page + " 页" : ""}</span><ArrowUpRightIcon size={15} className="source-open-icon" /></button>
                <span className="source-kind">{source.demo ? "演示原文" : "资料原文"}</span>
              </div>
              <p className="source-excerpt">{source.excerpt}</p>
            </div>}
          </section>}
        </div>
      </section>
  );
}

function AnswerMessage({ message, onSource, onToast }: AnswerActions & { message: Message }) {
  return (
    <article className="conversation-turn" aria-label="一轮问答">
      <div className="question-row">
        <div className="avatar user-avatar"><UserIcon size={23} weight="fill" aria-hidden="true" /></div>
        <div className="question-content"><p className="question-bubble">{message.question}</p><p className="message-time">{message.time}</p></div>
      </div>
      <AnswerResult answer={message.answer} id={message.id} label="回答结果" onSource={onSource} onToast={onToast} />
      {message.originalAnswer && <AnswerResult answer={message.originalAnswer} id={message.id + "-original"} label="原文检索结果" onSource={onSource} onToast={onToast} />}
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
};

export function ConversationView(props: Props) {
  return (
    <>
      {!props.messages.length && <div className="welcome" aria-label={props.libraryName + "问答"}>
        <h2><BookOpenTextIcon size={41} weight="fill" aria-hidden="true" /><span>你好，有什么我能帮你的吗？</span></h2>
      </div>}
      {props.messages.map((message) => <AnswerMessage key={message.id} message={message} onSource={props.onSource} onToast={props.onToast} />)}
      {props.busy && <div className="thinking" role="status"><SparkleIcon size={20} weight="fill" aria-hidden="true" /><span>{answerModeInfo[props.mode].busy}</span></div>}
    </>
  );
}
