import type { Answer, Conversation, KnowledgeDocument } from "./types";

export const libraries = [
  { id: "herbal", name: "中药基础资料" },
];

export const demoExcerpt = "本资料按名称、来源、性状、贮藏等栏目整理，便于查阅与核对。";

export const demoFullText = [
  "陈皮资料条目（演示资料）",
  "",
  "一、资料结构",
  demoExcerpt,
  "",
  "二、名称与来源",
  "本节用于整理资料中出现的条目名称、来源记录及对应的文献信息。",
  "",
  "三、性状记录",
  "本节用于收录原文中的描述性信息，并保留对应的引用位置。",
  "",
  "四、贮藏条目",
  "本节用于整理原文中有关贮藏的说明，具体内容应回到真实资料核对。",
  "",
  "以上内容仅用于展示界面与引用交互，不是真实药品文献或医疗建议。",
].join("\n");

export const initialAnswer: Answer = {
  title: "陈皮资料 · 内容概览",
  introduction: "根据已上传的演示资料，内容可按以下栏目阅读。",
  sections: [
    {
      title: "名称与来源",
      content: "资料首先介绍条目的名称与来源，梳理其常用名称和来源记录的写法与内容结构。",
      sourceIndex: 0,
    },
    {
      title: "性状记录",
      content: "资料按照描述性栏目整理原文记录，并提供相应的文字说明与引用位置。",
      sourceIndex: 0,
    },
    {
      title: "贮藏条目",
      content: "资料最后整理了原文中的贮藏说明；具体内容与适用条件，请以实际资料为准。",
      sourceIndex: 1,
    },
  ],
  sources: [
    { id: "sample-page-2", name: "陈皮资料.pdf", page: 2, excerpt: demoExcerpt, fullText: demoFullText, demo: true },
    {
      id: "sample-page-3",
      name: "陈皮资料.pdf",
      page: 3,
      excerpt: "本节用于整理原文中有关贮藏的说明，具体内容应回到真实资料核对。",
      fullText: demoFullText,
      demo: true,
    },
  ],
};

export const initialConversations: Conversation[] = [
  {
    id: "chenpi",
    libraryId: "herbal",
    title: "陈皮资料要点",
    messages: [{
      id: "initial-message",
      question: "帮我概括陈皮资料的内容，并标注来源。",
      time: "今天 10:24",
      answer: initialAnswer,
    }],
  },
  {
    id: "scope",
    libraryId: "herbal",
    title: "资料收录范围",
    messages: [{
      id: "scope-message",
      question: "当前知识库收录了哪些资料？",
      time: "今天 09:46",
      answer: {
        title: "从资料开始，建立你的知识库",
        introduction: "这里展示的是前端示例，可切换知识库、添加文本资料并核对引用。",
        sections: [
          { title: "基础条目", content: "收录示例资料的名称、来源与栏目说明。", sourceIndex: 0 },
          { title: "自己的资料", content: "上传 Markdown 或 TXT 后，可在浏览器中读取原文；PDF 和 Word 的正文解析尚待接入。", sourceIndex: 0 },
        ],
        sources: [{
          id: "scope-source", name: "基础条目.md",
          excerpt: "资料按主题归入对应知识库，引用保留资料名称和原文片段。",
          fullText: "# 基础条目\n\n资料按主题归入对应知识库，引用保留资料名称和原文片段。\n\n本文件为界面演示资料。",
          demo: true,
        }],
      },
    }],
  },
];

export const initialDocuments: KnowledgeDocument[] = [
  { id: "demo-pdf", libraryId: "herbal", name: "陈皮资料.pdf", status: "parsing", progress: 68, content: demoFullText, demo: true },
  { id: "demo-basics", libraryId: "herbal", name: "基础条目.md", status: "ready", progress: 100, content: "# 基础条目\n\n资料按主题归入对应知识库，引用保留资料名称和原文片段。", demo: true },
  { id: "demo-guide", libraryId: "herbal", name: "收录说明.pdf", status: "queued", progress: 0, content: "演示说明：上传的资料按照当前选中的知识库组织。", demo: true },
];

export function createAnswer(question: string, documents: KnowledgeDocument[]): Answer {
  const ready = documents.filter((doc) => doc.status === "ready" && doc.content.trim());
  const local = ready.filter((doc) => !doc.demo);
  if (local.length) {
    const terms = question.match(/[a-zA-Z0-9]+|[\u4e00-\u9fff]{2,}/g) ?? [];
    const candidates = local.flatMap((doc) => {
      const paragraphs = doc.content.split(/\n\s*\n|\n/).map((line) => line.trim()).filter(Boolean);
      return paragraphs.map((text, index) => ({
        doc, text, index,
        score: terms.reduce((n, term) => n + (text.includes(term) ? 3 : 0), 0)
          + (question.includes(doc.name.replace(/\.[^.]+$/, "")) ? 2 : 0),
      }));
    }).sort((a, b) => b.score - a.score);
    const matches = candidates.slice(0, 3);
    return {
      title: "从你的资料中找到这些内容",
      introduction: "以下为本地文本原文摘录，未调用 AI，也未生成医学结论。可点击引用核对完整内容。",
      sections: matches.map((match, index) => ({
        title: match.doc.name + " · 片段 " + (match.index + 1),
        content: match.text.slice(0, 300),
        sourceIndex: index,
      })),
      sources: matches.map((match) => ({
        id: match.doc.id + "-" + match.index,
        name: match.doc.name,
        excerpt: match.text,
        fullText: match.doc.content,
        demo: false,
      })),
    };
  }
  if (ready.some((doc) => doc.demo)) {
    return {
      ...initialAnswer,
      title: /陈皮/.test(question) ? initialAnswer.title : "资料问答 · 演示回答",
      introduction: "当前展示预设的资料问答示例，尚未连接 AI 服务。上传文本资料后可查看真实原文摘录。",
    };
  }
  return {
    title: "这个知识库还没有可读取的资料",
    introduction: "请先上传 Markdown 或 TXT 资料，再尝试提问。PDF、Word 需要接入解析服务。",
    sections: [],
    sources: [],
  };
}
