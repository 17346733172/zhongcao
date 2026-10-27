import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/lib/knowledge-answer.ts", import.meta.url), "utf8");
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


const reference = JSON.parse(await readFile(new URL("../../backend/resources/herbal-reference.json", import.meta.url), "utf8"));
const demo = { id: "demo", libraryId: "herbal", name: "陈皮资料.pdf", status: "ready", progress: 100, content: "预设陈皮示例", demo: true };

test("只有演示资料时不会对陈皮或 111 生成预设回答", () => {
  for (const question of ["陈皮", "111"]) {
    const answer = createAnswer(question, [demo]);
    assert.equal(answer.sections.length, 0);
    assert.equal(answer.sources.length, 0);
  }
});

test("111 在正式文档中未命中时不返回陈皮或其他原文", () => {
  const answer = createAnswer("111", [demo], reference);
  assert.match(answer.title, /未找到相关内容/);
  assert.deepEqual(answer.sources, []);
  assert.deepEqual(answer.sections, []);
});

test("真实上传文本也不会返回零分片段", () => {
  const answer = createAnswer("111", [{ id: "real", libraryId: "herbal", name: "陈皮.txt", content: "陈皮的测试原文", demo: false, status: "ready", progress: 100 }, demo]);
  assert.match(answer.title, /未找到/);
  assert.equal(answer.sources.length, 0);
  assert.equal(answer.sections.length, 0);
});

test("陈皮及完整中文问题均引用正式 Word 中对应的药材条目", () => {
  const index = reference.blocks.findIndex(block => block.type === "heading" && block.text.startsWith("陈皮（"));
  const expected = reference.blocks[index + 2].text;
  for (const question of ["陈皮", "陈皮有什么功效", "请介绍一下陈皮", "陈皮的用法用量"]) {
    const answer = createAnswer(question, [demo], reference);
    assert.ok(answer.sources.length > 0, question);
    assert.ok(answer.sections.some(section => section.content.includes(expected)), question);
    assert.ok(answer.sections.every(section => section.title.startsWith("陈皮（")), question);
    assert.ok(answer.sources.every(source => source.name === reference.name && !source.demo));
    assert.equal(answer.sources[0].fullText, reference.fullText);
    assert.deepEqual(answer.sources[0].blocks, reference.blocks);
    assert.equal(answer.sources[0].downloadUrl, reference.downloadUrl);
  }
});

test("数字与通用栏目词组合不会借栏目词误匹配其他药材", () => {
  for (const question of ["111有什么功效", "不存在的外星矿石", "１１１", "XYZ123"]) {
    const answer = createAnswer(question, [], reference);
    assert.match(answer.title, /未找到/, question);
    assert.equal(answer.sources.length, 0, question);
  }
});

test("陈皮和青皮同时检索时分别保留对应原文", () => {
  const answer = createAnswer("陈皮和青皮有什么区别", [], reference);
  assert.ok(answer.sections.some(section => section.title.startsWith("陈皮（")));
  assert.ok(answer.sections.some(section => section.title.startsWith("青皮（")));
  assert.equal(answer.sections.length, 2);
});

test("明确的资料概览请求可摘录真实资料，不对 111 做概览兜底", () => {
  const answer = createAnswer("帮我概括资料中的要点", [], reference);
  assert.match(answer.title, /资料概览/);
  assert.ok(answer.sources.length > 0);
  assert.ok(answer.sources.every(source => !source.demo));
  assert.equal(createAnswer("概括111", [], reference).sources.length, 0);
});

test("英文关键词忽略大小写，且允许资料中真实存在的数字", () => {
  const doc = { id: "real", libraryId: "herbal", name: "测试.txt", content: "ABC123 是测试标记。第二个记录号为 111。", demo: false, status: "ready", progress: 100 };
  assert.ok(createAnswer("abc123", [doc]).sources.length > 0);
  assert.ok(createAnswer("111", [doc]).sources.length > 0);
});


test("正式文档存在同名药材时仍可检索真实上传文本中的对应记录", () => {
  const doc = { id: "real", libraryId: "herbal", name: "补充记录.txt", content: "陈皮：这是一段用于核对的上传原文。", demo: false, status: "ready", progress: 100 };
  const answer = createAnswer("陈皮", [doc], reference);
  assert.ok(answer.sources.some(source => source.name === doc.name && source.fullText === doc.content));
  assert.ok(answer.sources.some(source => source.name === reference.name));
});
