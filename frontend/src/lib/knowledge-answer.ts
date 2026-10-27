import type { Answer, KnowledgeDocument, Source } from "./types";

type Passage = { source: Source; title: string; text: string; index: number; headingKey: string };
const normalize = (text: string) => text.normalize("NFKC").toLowerCase();
const ignoredTerms = new Set([
  "请", "请问", "帮", "帮我", "我", "给", "给我", "的", "了", "和", "与", "及", "在", "中", "中的", "里", "是", "有", "吗", "呢",
  "什么", "怎么", "如何", "哪些", "有哪些", "一下", "相关", "关于", "当前", "查看", "查找", "查询", "介绍", "说明",
  "概括", "总结", "概览", "收录", "范围", "要点", "资料", "内容", "原文", "知识库", "药材", "条目", "中药",
]);
const fieldTerms = new Set(["功效", "作用", "应用", "用法", "用量", "性味", "归经", "禁忌", "注意", "事项", "区别"]);

function queryTerms(question: string) {
  const segmenter = new Intl.Segmenter("zh-CN", { granularity: "word" });
  const words = Array.from(segmenter.segment(normalize(question)))
    .filter((item) => item.isWordLike)
    .map((item) => item.segment)
    .filter((word) => !ignoredTerms.has(word));
  const specific = words.filter((word) => !fieldTerms.has(word));
  return [...new Set(specific.length ? specific : words)];
}

function referencePassages(source: Source): Passage[] {
  if (!source.blocks?.length) return textPassages(source);
  const passages: Passage[] = [];
  let title = source.name;
  let lines: string[] = [];
  let index = 0;
  function flush() {
    if (!lines.length) return;
    const name = normalize(title.split(/[（(]/)[0].trim());
    passages.push({ source, title, text: [title, ...lines].join("\n"), index, headingKey: /^[\p{Script=Han}]{2,8}$/u.test(name) ? name : "" });
    lines = [];
  }
  source.blocks.forEach((block, blockIndex) => {
    if (block.type === "heading") {
      flush();
      title = block.text;
      index = blockIndex;
    } else if (block.type === "paragraph") lines.push(block.text);
    else lines.push(block.rows.map((row) => row.join("\t")).join("\n"));
  });
  flush();
  return passages;
}

function textPassages(source: Source): Passage[] {
  return source.fullText.split(/\n\s*\n|\n/).map((text, index) => ({
    source, text: text.trim(), index, title: source.name + " · 片段 " + (index + 1), headingKey: "",
  })).filter((passage) => passage.text);
}

export function createAnswer(question: string, documents: KnowledgeDocument[], reference?: Source): Answer {
  const sources: Source[] = documents.filter((doc) => !doc.demo && doc.status === "ready" && doc.content.trim()).map((doc) => ({
    id: doc.id, name: doc.name, excerpt: "", fullText: doc.content, demo: false,
  }));
  if (reference && !reference.demo && reference.fullText.trim()) sources.unshift(reference);
  if (!sources.length) return {
    title: "这个知识库还没有可读取的真实资料",
    introduction: "请先加载中药基础资料或添加 MD / TXT 文本，再尝试提问。",
    sections: [], sources: [], mode: "no_match",
  };

  const query = normalize(question);
  const terms = queryTerms(question);
  const overview = !terms.length && /概括|总结|收录|范围|概览|要点/.test(query);
  const passages = sources.flatMap((source) => source.blocks ? referencePassages(source) : textPassages(source));
  const namedTopics = [...new Set(passages.map((passage) => passage.headingKey).filter((name) => name && query.includes(name)))];
  const candidates = passages.map((passage) => {
    const text = normalize(passage.text);
    const heading = normalize(passage.title);
    const namedMatch = namedTopics.some((name) => passage.headingKey === name || normalize(passage.source.name).includes(name) || (!passage.source.blocks && text.includes(name)));
    const matches = terms.filter((term) => text.includes(term) || normalize(passage.source.name).includes(term));
    const score = namedTopics.length ? (namedMatch ? 100 + matches.length : 0)
      : terms.length > 0 && matches.length === terms.length ? matches.reduce((total, term) => total + (heading.includes(term) ? 6 : 2), 0) : 0;
    return { ...passage, score };
  }).filter((passage) => overview || passage.score > 0).sort((a, b) => b.score - a.score);
  const matches = overview ? sources.flatMap((source) => candidates.find((passage) => passage.source.id === source.id) ?? []).slice(0, 3) : candidates.slice(0, 3);
  if (!matches.length) return {
    title: "未找到相关内容",
    introduction: "当前资料中没有找到匹配的原文。请尝试其他药材名称或关键词。可尝试其他关键词，或切换回答方式。",
    sections: [], sources: [], mode: "no_match",
  };
  return {
    mode: "extract",
    title: overview ? "当前资料概览 · 原文摘录" : "找到与问题相关的原文",
    introduction: "以下为关键词匹配到的资料原文摘录，未调用 AI。可点击引用核对完整文档。",
    sections: matches.map((match, index) => ({ title: match.title, content: match.text.length > 1500 ? match.text.slice(0, 1500) + "…" : match.text, sourceIndex: index })),
    sources: matches.map((match) => ({ ...match.source, id: match.source.id + "-" + match.index, excerpt: match.text.length > 1500 ? match.text.slice(0, 1500) + "…" : match.text, demo: false })),
  };
}
