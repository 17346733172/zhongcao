import type { Answer, AnswerMode, Message } from "./types";

export const answerModeInfo: Record<AnswerMode, { label: string; description: string; note: string; busy: string }> = {
  ai: {
    label: "AI 问答",
    description: "直接使用 DeepSeek 回答，不使用知识库",
    note: "内容由 AI 生成，未使用知识库",
    busy: "正在等待 DeepSeek 生成回答…",
  },
  both: {
    label: "AI + 原文",
    description: "生成 AI 回答，并展示独立的原文检索结果",
    note: "AI 回答和原文检索已开启，请核对引用资料",
    busy: "正在生成 AI 回答并整理原文检索结果…",
  },
};

export function toggleOriginalSearch(mode: AnswerMode): AnswerMode {
  return mode === "both" ? "ai" : "both";
}

export async function runAnswerMode(
  mode: AnswerMode,
  question: string,
  generate: (question: string) => Promise<Answer>,
  extract: (question: string) => Answer,
): Promise<Pick<Message, "answer" | "originalAnswer">> {
  // Only whole-message greetings bypass retrieval; a greeting before a question does not.
  if (/^(?:你好(?:呀|啊)?|您好|嗨|哈[喽啰罗]|早上好|上午好|中午好|下午好|晚上好|hello|hi|hey)[\s!！?？,.，。~～]*$/i.test(question.normalize("NFKC").trim())) {
    return { answer: {
      mode: "greeting", title: "你好！",
      introduction: "我是本草知问，可以帮你查阅中药资料、整理相关知识。你想了解哪味中药，或哪方面的问题？",
      sections: [], sources: [],
    } };
  }
  const answer = await generate(question);
  if (mode === "both" && answer.mode !== "clarification") {
    const originalAnswer = extract(answer.resolvedQuestion || question);
    if (answer.mode === "no_match" && originalAnswer.mode === "no_match") return { answer };
    return { answer, originalAnswer };
  }
  return { answer };
}
