import { api } from "./api";
import type { Answer, Message } from "./types";
import { buildChatHistory } from "./conversation-history";

export type AIStatus = { provider: string; configured: boolean; model: string };

export function loadAIStatus() {
  return api<AIStatus>("/ai/status");
}

export function generateAnswer(question: string, signal: AbortSignal, messages: Message[] = [], useKnowledge = false) {
  return api<Answer>("/chat", {
    method: "POST",
    body: JSON.stringify({ question, history: buildChatHistory(messages, useKnowledge), use_knowledge: useKnowledge }),
    signal: AbortSignal.any([signal, AbortSignal.timeout(45000)]),
  });
}
