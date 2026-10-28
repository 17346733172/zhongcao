import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/answer-mode.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } });
const { toggleAnswerOption, isAnswerOptionSelected, runAnswerMode } = await import("data:text/javascript;base64," + Buffer.from(outputText).toString("base64"));
const aiAnswer = { mode: "generated", title: "AI 回答", introduction: "", sections: [{ title: "归纳", content: "已生成", sourceIndex: 0 }], sources: [{ id: "ai-source" }] };
const originalAnswer = { mode: "extract", title: "原文摘录", introduction: "", sections: [{ title: "原文", content: "原文内容", sourceIndex: 0 }], sources: [{ id: "original-source" }] };

test("两个选项独立切换，可从任意组合取消或增加一个选项", () => {
  const transitions = {
    none: { ai: "ai", extract: "extract" },
    ai: { ai: "none", extract: "both" },
    extract: { ai: "both", extract: "none" },
    both: { ai: "extract", extract: "ai" },
  };
  for (const [mode, options] of Object.entries(transitions)) {
    for (const [option, expected] of Object.entries(options)) {
      assert.equal(toggleAnswerOption(mode, option), expected);
      const other = option === "ai" ? "extract" : "ai";
      assert.equal(isAnswerOptionSelected(mode, other), isAnswerOptionSelected(expected, other));
    }
  }
});

test("都不选时不发送模型请求，也不执行原文检索", async () => {
  const unexpected = () => assert.fail("未选择时不应执行服务");
  await assert.rejects(runAnswerMode("none", "陈皮", unexpected, unexpected), /请选择/);
});

test("只选 AI 时不附加原文检索结果，只选原文时不调用模型", async () => {
  const unexpected = () => assert.fail("不应调用未选中的功能");
  assert.deepEqual(await runAnswerMode("ai", "陈皮", async () => aiAnswer, unexpected), { answer: aiAnswer });
  assert.deepEqual(await runAnswerMode("extract", "陈皮", unexpected, () => originalAnswer), { answer: originalAnswer });
});

test("同时选中时只调用一次生成，按已解析追问检索并分别保留引用编号", async () => {
  let calls = 0;
  const generated = { ...aiAnswer, resolvedQuestion: "陈皮：作用？" };
  const result = await runAnswerMode("both", "作用？", async question => { calls++; assert.equal(question, "作用？"); return generated; }, question => { assert.equal(question, "陈皮：作用？"); return originalAnswer; });
  assert.equal(calls, 1);
  assert.deepEqual(result, { answer: generated, originalAnswer });
  assert.equal(result.answer.sources[result.answer.sections[0].sourceIndex].id, "ai-source");
  assert.equal(result.originalAnswer.sources[result.originalAnswer.sections[0].sourceIndex].id, "original-source");
});

test("双选需要澄清时不猜测原文，生成失败也不伪装为成功", async () => {
  const clarification = { ...aiAnswer, mode: "clarification", sections: [], sources: [] };
  const unexpected = () => assert.fail("不应继续原文检索");
  assert.deepEqual(await runAnswerMode("both", "作用？", async () => clarification, unexpected), { answer: clarification });
  await assert.rejects(runAnswerMode("both", "陈皮", async () => { throw new Error("生成失败"); }, unexpected), /生成失败/);
});
