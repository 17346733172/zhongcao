import { api } from "./api";
import type { Answer } from "./types";

export type AIStatus = { provider: string; configured: boolean; model: string };

export function loadAIStatus() {
  return api<AIStatus>("/ai/status");
}

export function generateAnswer(question: string, signal: AbortSignal) {
  return api<Answer>("/chat", {
    method: "POST",
    body: JSON.stringify({ question }),
    signal: AbortSignal.any([signal, AbortSignal.timeout(45000)]),
  });
}
