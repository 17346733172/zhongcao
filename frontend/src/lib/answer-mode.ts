import type { Answer, AnswerMode, AnswerOption, Message } from "./types";

export const answerModeInfo: Record<AnswerMode, { label: string; description: string; note: string; busy: string }> = {
  none: {
    label: "未选择",
    description: "请选择回答方式，可同时选择 AI 回答和原文检索",
    note: "请选择 AI 回答或原文检索，也可以同时选择",
    busy: "",
  },
  ai: {
    label: "AI 问答",
    description: "优先依据知识库资料，AI 补充单独标注",
    note: "内容由 AI 生成，请核对引用资料；AI 补充单独标注",
    busy: "正在检索资料并等待 DeepSeek 生成回答…",
  },
  extract: {
    label: "原文检索",
    description: "从中药基础资料和共享文本中查找原文",
    note: "原文检索，请核对引用资料",
    busy: "正在检索资料片段…",
  },
  both: {
    label: "AI + 原文",
    description: "生成 AI 回答，并展示独立的原文检索结果",
    note: "AI 回答和原文检索已开启，请核对引用资料",
    busy: "正在生成 AI 回答并整理原文检索结果…",
  },
};

export function isAnswerOptionSelected(mode: AnswerMode, option: AnswerOption) {
  return mode === option || mode === "both";
}

export function toggleAnswerOption(mode: AnswerMode, option: AnswerOption): AnswerMode {
  const ai = isAnswerOptionSelected(mode, "ai") !== (option === "ai");
  const extract = isAnswerOptionSelected(mode, "extract") !== (option === "extract");
  return ai ? extract ? "both" : "ai" : extract ? "extract" : "none";
}

export async function runAnswerMode(
  mode: AnswerMode,
  question: string,
  generate: (question: string) => Promise<Answer>,
  extract: (question: string) => Answer,
): Promise<Pick<Message, "answer" | "originalAnswer">> {
  if (mode === "none") throw new Error("请选择 AI 回答或原文检索后再发送。");
  if (mode === "extract") return { answer: extract(question) };
  const answer = await generate(question);
  if (mode === "both" && answer.mode !== "clarification") {
    return { answer, originalAnswer: extract(answer.resolvedQuestion || question) };
  }
  return { answer };
}
