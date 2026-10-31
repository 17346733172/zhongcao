import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/answer-mode.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } });
const { answerModeInfo, toggleOriginalSearch, runAnswerMode } = await import("data:text/javascript;base64," + Buffer.from(outputText).toString("base64"));
const aiAnswer = { mode: "generated", title: "AI 回答", introduction: "", sections: [{ title: "归纳", content: "已生成", sourceIndex: 0 }], sources: [{ id: "ai-source" }] };
const originalAnswer = { mode: "extract", title: "原文摘录", introduction: "", sections: [{ title: "原文", content: "原文内容", sourceIndex: 0 }], sources: [{ id: "original-source" }] };

let componentModules;
function loadAnswerComponents() {
  return componentModules ??= (async () => {
    const require = createRequire(import.meta.url);
    const [icons, markdown, gfm] = await Promise.all([import("@phosphor-icons/react"), import("react-markdown"), import("remark-gfm")]);
    const dependencies = { "@/lib/answer-mode": { answerModeInfo }, "@phosphor-icons/react": icons, "react-markdown": markdown, "remark-gfm": gfm };
    async function compile(file) {
      const code = await readFile(new URL(file, import.meta.url), "utf8");
      const { outputText } = ts.transpileModule(code, { compilerOptions: {
        module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX,
      } });
      const exports = {};
      new Function("require", "exports", outputText)(name => dependencies[name] ?? require(name), exports);
      return exports;
    }
    const markdownComponent = await compile("../src/components/answer-markdown.tsx");
    dependencies["./answer-markdown"] = markdownComponent;
    return { ...markdownComponent, ...await compile("../src/components/conversation-view.tsx") };
  })();
}

test("原文开关反复切换后，发送始终调用 AI 一次，原文只按需附加", async () => {
  let mode = "ai";
  let generated = 0, extracted = 0;
  for (let turn = 0; turn < 5; turn++) {
    const result = await runAnswerMode(mode, "陈皮", async () => { generated++; return aiAnswer; }, () => { extracted++; return originalAnswer; });
    assert.equal(generated, turn + 1);
    assert.equal(result.answer, aiAnswer);
    assert.equal(result.originalAnswer, mode === "both" ? originalAnswer : undefined);
    mode = toggleOriginalSearch(mode);
    assert.equal(mode, turn % 2 === 0 ? "both" : "ai");
  }
  assert.equal(extracted, 2);
});

test("默认发送 AI 回答，不附加原文检索结果", async () => {
  const unexpected = () => assert.fail("不应调用未选中的功能");
  assert.deepEqual(await runAnswerMode("ai", "陈皮", async () => aiAnswer, unexpected), { answer: aiAnswer });
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

test("纯问候在默认和附加原文模式下只返回欢迎回复，不查询资料或模型", async () => {
  const unexpected = () => assert.fail("纯问候不应调用服务");
  for (const mode of ["ai", "both"]) {
    for (const question of ["你好", "  你好！  ", "您好。", "你好呀～", "Hi!", "Ｈｅｌｌｏ！"]) {
      const result = await runAnswerMode(mode, question, unexpected, unexpected);
      assert.equal(result.answer.mode, "greeting");
      assert.equal(result.answer.title, "你好！");
      assert.deepEqual(result.answer.sources, []);
      assert.deepEqual(result.answer.sections, []);
      assert.equal(result.originalAnswer, undefined);
    }
  }
});

test("问候后带有实际问题时仍按所选方式回答", async () => {
  for (const question of ["你好，陈皮有什么功效？", "您好，请问黄芪的禁忌", "Hi, 陈皮"]) {
    const result = await runAnswerMode("both", question,
      async value => { assert.equal(value, question); return aiAnswer; },
      value => { assert.equal(value, question); return originalAnswer; });
    assert.deepEqual(result, { answer: aiAnswer, originalAnswer });
  }
});

test("双选都未命中时仅保存一次空结果，其余情况保留两路原始响应", async () => {
  const noMatch = { mode: "no_match", title: "未找到相关内容", introduction: "没有匹配资料", sections: [], sources: [] };
  assert.deepEqual(await runAnswerMode("both", "111", async () => noMatch, () => ({ ...noMatch, introduction: "无原文" })), { answer: noMatch });
  assert.deepEqual(await runAnswerMode("both", "陈皮", async () => noMatch, () => originalAnswer), { answer: noMatch, originalAnswer });
  assert.deepEqual(await runAnswerMode("both", "陈皮", async () => aiAnswer, () => noMatch), { answer: aiAnswer, originalAnswer: noMatch });
});

test("实际回答组件只显示有内容的结果，全空时仅显示一条提示", async () => {
  const viewExports = await loadAnswerComponents();
  const noMatch = { mode: "no_match", title: "资料不足以回答这个问题", introduction: "没有匹配资料", sections: [], sources: [] };
  for (const [answer, original, showSources, count, hasAI, hasOriginal, hasEmpty] of [
    [noMatch, originalAnswer, true, 1, false, true, false],
    [aiAnswer, noMatch, true, 1, true, false, false],
    [noMatch, noMatch, true, 1, false, false, true],
    [noMatch, undefined, true, 1, false, false, true],
    [aiAnswer, originalAnswer, true, 2, true, true, false],
    [aiAnswer, originalAnswer, false, 1, true, false, false],
    [noMatch, originalAnswer, false, 1, false, false, true],
  ]) {
    const html = renderToStaticMarkup(createElement(viewExports.ConversationView, {
      mode: showSources ? "both" : "ai", busy: false, libraryName: "测试资料",
      messages: [{ id: "turn", question: "测试问题", time: "10:00", answer, originalAnswer: original, showSources }],
      onSource() {}, onToast() {},
    }));
    assert.equal((html.match(/class="answer-row"/g) ?? []).length, count);
    assert.equal((html.match(/class="quiet-button copy-answer"/g) ?? []).length, count);
    assert.equal(html.includes("已生成"), hasAI);
    assert.equal(html.includes("原文内容"), hasOriginal);
    assert.equal(html.includes(noMatch.title), hasEmpty);
    assert.equal((html.match(/class="source-card"/g) ?? []).length, hasOriginal ? 1 : 0);
  }
});

test("生成正文渲染加粗、列表和表格且不执行 HTML，原文摘录保留原字面文本", async () => {
  const { AnswerMarkdown, ConversationView } = await loadAnswerComponents();
  const html = renderToStaticMarkup(createElement(AnswerMarkdown, { content: "这是**重点**。\n\n- **条目一**：内容\n- 条目二\n\n1. 第一步\n2. 第二步\n\n| 栏目 | 说明 |\n| --- | --- |\n| 示例 | 测试 |\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n[不安全链接](javascript:alert)" }));
  assert.match(html, /<strong>重点<\/strong>/);
  assert.match(html, /<ul>/); assert.match(html, /<ol>/);
  assert.match(html, /aria-label="回答表格"/); assert.match(html, /<table>/);
  assert.doesNotMatch(html, /<script|<img|onerror|javascript:/);
  const original = { ...originalAnswer, sections: [{ title: "原文", content: "**原文保留**\n- 原文符号" }], sources: [] };
  const extractHtml = renderToStaticMarkup(createElement(ConversationView, {
    mode: "both", messages: [{ id: "original", question: "原文", time: "10:00", answer: original, showSources: true }],
    busy: false, libraryName: "测试", onSource() {}, onToast() {},
  }));
  assert.match(extractHtml, /\*\*原文保留\*\*/);
  assert.doesNotMatch(extractHtml, /<strong>|<ul>/);
});
