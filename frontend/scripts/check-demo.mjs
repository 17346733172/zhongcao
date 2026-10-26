import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/demo-data.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
});
const { createAnswer } = await import("data:text/javascript;base64," + Buffer.from(outputText).toString("base64"));

test("空知识库不产生虚构引用", () => {
  const answer = createAnswer("请概括资料", []);
  assert.equal(answer.sources.length, 0);
  assert.equal(answer.sections.length, 0);
  assert.match(answer.title, /没有可读取/);
});

test("尚未解析的 PDF 不作为可查询正文", () => {
  const answer = createAnswer("查看内容", [{
    id: "pdf", libraryId: "herbal", name: "待解析.pdf",
    status: "needs-parser", progress: 100, content: "", demo: false,
  }]);
  assert.equal(answer.sources.length, 0);
});

test("本地文本的回答保留真实原文，且不混入示例来源", () => {
  const content = "# 我的资料\n\n测试条目：这是用于核对的原文，不是医学建议。";
  const answer = createAnswer("测试条目", [{
    id: "local", libraryId: "notes", name: "我的资料.md",
    status: "ready", progress: 100, content, demo: false,
  }, {
    id: "demo", libraryId: "notes", name: "示例.pdf",
    status: "ready", progress: 100, content: "不应混入的预设文本", demo: true,
  }]);
  assert.ok(answer.sources.length > 0);
  for (const item of answer.sources) {
    assert.equal(item.name, "我的资料.md");
    assert.equal(item.fullText, content);
    assert.equal(item.demo, false);
  }
  assert.match(answer.introduction, /未调用 AI/);
});
