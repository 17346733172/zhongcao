import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";
const source = await readFile(new URL("../src/lib/conversation-history.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } });
const { buildChatHistory } = await import("data:text/javascript;base64," + Buffer.from(outputText).toString("base64"));
const message = (question, extra = {}) => ({ id: question, question, time: "今天", answer: { title: "回答", introduction: "", sections: [], sources: [], ...extra } });
test("新对话不携带其他对话的历史", () => { assert.deepEqual(buildChatHistory([]), []); });
test("只发送最近五轮并保持顺序", () => { assert.deepEqual(buildChatHistory(Array.from({ length: 8 }, (_, i) => message(String(i)))).map(x => x.question), ["3", "4", "5", "6", "7"]); });
test("连续省略主题的追问保留已解析的主题", () => { assert.equal(buildChatHistory([message("作用？", { resolvedQuestion: "陈皮：作用？" })])[0].question, "陈皮：作用？"); });
test("上下文有限长且不发送旧原文和引用对象", () => {
  const result = buildChatHistory([message("陈".repeat(900), { title: "答".repeat(1500), sources: [{ fullText: "不应发送的整本文档" }] })]);
  assert.equal(result[0].question.length, 500); assert.equal(result[0].answer.length, 1000); assert.ok(!JSON.stringify(result).includes("不应发送的整本文档"));
});
test("历史摘要保留 AI 补充类别", () => { assert.match(buildChatHistory([message("陈皮", { sections: [{ title: "补充", content: "通用知识", origin: "ai_supplement" }] })])[0].answer, /AI 补充，非文档原文/); });
