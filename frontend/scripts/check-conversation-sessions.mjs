import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const icons = await import("@phosphor-icons/react");
const code = await readFile(new URL("../src/components/conversation-sessions.tsx", import.meta.url), "utf8");
const compiled = ts.transpileModule(code, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 } }).outputText;
const module = { exports: {} };
class FixedDate extends Date { static now() { return Date.parse("2026-11-19T06:32:00Z"); } }
new Function("require", "module", "exports", "Date", compiled)(name => name === "@phosphor-icons/react" ? icons : require(name), module, module.exports, FixedDate);
const { ConversationSessions } = module.exports;
const noop = () => {};
const conversation = (id, answeredAt, title = id) => ({ id, title, libraryId: "herbal", messages: [{ id: id + "-turn", answeredAt, time: "未记录", question: title, answer: { title: "示例", sections: [], sources: [] }, showSources: true }] });
function render(conversations, activeId = null) {
  const html = renderToStaticMarkup(createElement(ConversationSessions, { conversations, activeId, open: false, onNew: noop, onSelect: noop, onClose: noop }));
  return html.match(/<aside[^>]*>([\s\S]*?)<\/aside>/)[1];
}

test("历史按北京时间归日，UTC 前一天的零点后回答仍属于今天", () => {
  const html = render([
    conversation("北京时间今天", "2026-11-18T16:20:00Z"),
    conversation("北京时间昨天", "2026-11-18T15:59:00Z"),
    conversation("较早会话", "2026-11-17T06:00:00Z"),
  ]);
  const groups = [...html.matchAll(/<section class="session-day-group"[^>]*aria-label="([^"]+)"[^>]*>([\s\S]*?)<\/section>/g)];
  assert.deepEqual(groups.map(m => m[1]), ["今天", "昨天", "更早"]);
  assert.match(groups[0][2], /北京时间今天/);
  assert.doesNotMatch(groups[0][2], /北京时间昨天/);
  assert.match(groups[0][2], /00:20/);
  assert.match(groups[1][2], /北京时间昨天/);
  assert.match(groups[1][2], /23:59/);
  assert.match(groups[2][2], /较早会话/);
});

test("继续旧会话后按最后回答排序，排序不改动传入会话数组", () => {
  const items = [conversation("较新创建", "2026-11-19T04:00:00Z"), conversation("旧会话刚继续", "2026-11-19T06:30:00Z")];
  const html = render(items, "旧会话刚继续");
  assert(html.indexOf('title="旧会话刚继续"') < html.indexOf('title="较新创建"'));
  assert.deepEqual(items.map(item => item.id), ["较新创建", "旧会话刚继续"]);
  assert.equal((html.match(/aria-current="true"/g) ?? []).length, 1);
});

test("缺少或非法时间的旧会话单独归类，保留原时间文字", () => {
  const html = render([conversation("缺少时间", undefined), conversation("非法时间", "invalid-date")]);
  assert.match(html, /aria-label="本页会话"/);
  assert.doesNotMatch(html, /aria-label="今天"|aria-label="昨天"|Invalid Date/);
  assert.match(html, /未记录/);
});

test("空历史保留真实空状态、新建入口和账号保存说明，不填示例记录", () => {
  const html = render([]);
  assert.match(html, /暂无历史会话/);
  assert.match(html, /新会话/);
  assert.match(html, /保存在当前账号，刷新后可继续/);
  assert.doesNotMatch(html, /class="session-history-item|class="session-day-group/);
});

test("历史摘要未加载正文时仍按实际时间归组并显示已保存轮数", () => {
  const html = render([{ id: "saved", libraryId: "herbal", title: "已保存会话", messages: [], messagesLoaded: false, updatedAt: "2026-11-19T06:00:00Z", messageCount: 12 }]);
  assert.match(html, /aria-label="今天"/);
  assert.match(html, /12 轮/);
  assert.match(html, /14:00/);
  assert.doesNotMatch(html, /暂无历史会话/);
});
