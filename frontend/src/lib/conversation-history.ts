import type { Message } from "./types";

export type ChatHistoryTurn = { question: string; answer: string };

export function buildChatHistory(messages: Message[], useKnowledge = false): ChatHistoryTurn[] {
  return messages.filter((message) => message.answer.mode !== "greeting" && Boolean(message.showSources) === useKnowledge).slice(-5).map((message) => ({
    question: (message.answer.resolvedQuestion || message.question).slice(0, 500),
    answer: [message.answer.title, ...message.answer.sections.map((section) =>
      (section.origin === "ai_supplement" ? "【AI 补充，非文档原文】" : section.origin === "document" ? "【资料依据】" : "")
      + section.title + "：" + section.content,
    )].join("\n").slice(0, 1000),
  }));
}
