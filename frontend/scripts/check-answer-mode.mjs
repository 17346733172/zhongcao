import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import test from "node:test";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/answer-mode.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } });
const { answerModeInfo, DEFAULT_ANSWER_MODE, runAnswerMode } = await import("data:text/javascript;base64," + Buffer.from(outputText).toString("base64"));
const aiAnswer = { mode: "generated", title: "AI 回答", introduction: "", sections: [{ title: "归纳", content: "已生成", sourceIndex: 0 }], sources: [{ id: "ai-source" }] };
const originalAnswer = { mode: "extract", title: "原文摘录", introduction: "", sections: [{ title: "原文", content: "原文内容", sourceIndex: 0 }], sources: [{ id: "original-source" }] };

let componentModules;
function loadAnswerComponents() {
  return componentModules ??= (async () => {
    const require = createRequire(import.meta.url);
    const [icons, markdown, gfm] = await Promise.all([import("@phosphor-icons/react"), import("react-markdown"), import("remark-gfm")]);
    const dependencies = { "@/lib/answer-mode": { answerModeInfo, DEFAULT_ANSWER_MODE }, "@phosphor-icons/react": icons, "react-markdown": markdown, "remark-gfm": gfm };
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
    return { ...markdownComponent, ...await compile("../src/components/conversation-view.tsx"), ...await compile("../src/components/question-composer.tsx") };
  })();
}

test("默认固定使用原文加 AI，发送一次生成并附加原文", async () => {
  assert.equal(DEFAULT_ANSWER_MODE, "both");
  let generated = 0, extracted = 0;
  const result = await runAnswerMode(DEFAULT_ANSWER_MODE, "陈皮", async () => { generated++; return aiAnswer; }, () => { extracted++; return originalAnswer; });
  assert.equal(generated, 1);
  assert.equal(extracted, 1);
  assert.deepEqual(result, { answer: aiAnswer, originalAnswer });
});

test("输入框没有原文开关，默认请求启用知识库及其历史", async () => {
  const { QuestionComposer } = await loadAnswerComponents();
  const html = renderToStaticMarkup(createElement(QuestionComposer, {
    draft: "陈皮", busy: false, disabled: false, canWrite: false, uploading: false,
    error: "", status: null, statusError: "", inputRef: { current: null },
    onDraft() {}, onSubmit() {}, onKeyDown() {}, onAttach() {},
  }));
  assert.doesNotMatch(html, /answer-mode-switch|aria-pressed|原文检索<\/button>/);
  assert.match(html, /基于知识库原文生成回答/);
  assert.match(html, /aria-label="发送"/);
  const code = await readFile(new URL("../src/lib/chat-api.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(code, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } });
  const exports = {};
  const messages = [{ id: "previous-turn" }];
  const history = [{ question: "陈皮", answer: "上轮回答" }];
  let request;
  new Function("require", "exports", outputText)(name => {
    if (name === "./api") return { api: (url, options) => { request = { url, ...options }; return Promise.resolve(aiAnswer); } };
    if (name === "./conversation-history") return { buildChatHistory: (actual, useKnowledge) => {
      assert.equal(actual, messages); assert.equal(useKnowledge, true); return history;
    } };
    assert.fail("Unexpected dependency " + name);
  }, exports);
  await exports.generateAnswer("作用？", new AbortController().signal, messages);
  assert.equal(request.url, "/chat");
  assert.deepEqual(JSON.parse(request.body), { question: "作用？", history, use_knowledge: true });
});

test("内部兼容普通 AI 调用时不附加原文", async () => {
  const unexpected = () => assert.fail("不应调用未选中的功能");
  assert.deepEqual(await runAnswerMode("ai", "陈皮", async () => aiAnswer, unexpected), { answer: aiAnswer });
});

test("向量模式原文直接使用服务端召回片段，保留引用并跳过浏览器关键词重检", async () => {
  const sources = [{ id: "md-chunk", name: "中药.md", excerpt: "陈皮：理气健脾。", fullText: "# 陈皮\n理气健脾。", demo: false }];
  const vector = { ...aiAnswer, retrievalMethod: "vector", retrievedSources: sources };
  const result = await runAnswerMode("both", "胸口痞闷", async () => vector, () => assert.fail("不能再次进行关键词检索"));
  assert.equal(result.originalAnswer.mode, "extract");
  assert.equal(result.originalAnswer.sources, sources);
  assert.equal(result.originalAnswer.sections[0].content, sources[0].excerpt);
  assert.equal(result.originalAnswer.sections[0].sourceIndex, 0);
  const declined = await runAnswerMode("both", "胸口痞闷", async () => ({ ...vector, mode: "no_match", sections: [], sources: [] }), () => assert.fail("不能重检"));
  assert.equal(declined.originalAnswer.sources, sources);
  const empty = { ...vector, mode: "no_match", sections: [], sources: [], retrievedSources: [] };
  assert.deepEqual(await runAnswerMode("both", "111", async () => empty, () => assert.fail("不能重检")), { answer: empty });
  assert.deepEqual(await runAnswerMode("ai", "陈皮", async () => vector, () => assert.fail("不能读取原文")), { answer: vector });
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

test("每轮只显示 AI 回答或状态提示，旧会话的独立原文摘录也不显示", async () => {
  const viewExports = await loadAnswerComponents();
  const noMatch = { mode: "no_match", title: "资料不足以回答这个问题", introduction: "没有匹配资料", sections: [], sources: [] };
  for (const [answer, original, showSources, count, hasAI, hasOriginal, hasEmpty] of [
    [noMatch, originalAnswer, true, 1, false, false, true],
    [aiAnswer, noMatch, true, 1, true, false, false],
    [noMatch, noMatch, true, 1, false, false, true],
    [noMatch, undefined, true, 1, false, false, true],
    [aiAnswer, originalAnswer, true, 1, true, false, false],
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
    assert.equal((html.match(/class="source-card"/g) ?? []).length, 0);
    assert.doesNotMatch(html, /aria-label="引用资料"/);
    assert.doesNotMatch(html, /aria-label="原文检索结果"/);
    assert.equal((html.match(/class="citation"/g) ?? []).length, hasAI && showSources ? 1 : 0);
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
