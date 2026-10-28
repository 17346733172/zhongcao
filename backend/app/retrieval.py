"""Server-owned lexical retrieval for the reference document and saved text."""
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class Passage:
    source: dict
    title: str
    text: str
    index: int
    topic: str = ""


def normalize(text):
    return unicodedata.normalize("NFKC", text).casefold()


def passages_for(source):
    if not source.get("blocks"):
        return [Passage(source, source["name"] + f" · 片段 {i + 1}", text.strip(), i)
                for i, text in enumerate(source["fullText"].splitlines()) if text.strip()]
    result = []
    title, lines, index = source["name"], [], 0

    def flush():
        if lines:
            name = normalize(re.split(r"[（(]", title)[0].strip())
            topic = name if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", name) else ""
            result.append(Passage(source, title, "\n".join([title, *lines]), index, topic))

    for i, block in enumerate(source["blocks"]):
        if block["type"] == "heading":
            flush()
            title, lines, index = block["text"], [], i
        elif block["type"] == "paragraph":
            lines.append(block["text"])
        else:
            lines.append("\n".join("\t".join(row) for row in block["rows"]))
    flush()
    return result


QUESTION_WORDS = sorted([
    "请介绍一下", "帮我查找", "请帮我", "用法用量", "使用注意", "有什么区别", "有什么", "是什么", "有哪些",
    "请问", "帮我", "给我", "介绍", "一下", "怎么", "如何", "什么", "哪些", "查找", "查看", "查询",
    "功效", "作用", "用法", "用量", "性味", "归经", "应用", "区别", "关于", "相关", "资料", "原文", "当前",
    "请", "的", "和", "与", "及", "吗", "呢",
], key=len, reverse=True)


def retrieve(question, documents, reference):
    sources = [reference] if reference and not reference.get("demo") and reference.get("fullText", "").strip() else []
    sources += [{"id": doc["id"], "name": doc["name"], "fullText": doc["content"], "demo": False}
                for doc in documents if not doc.get("demo") and doc.get("content", "").strip() and doc.get("status", "ready") == "ready"]
    passages = [item for source in sources for item in passages_for(source)]
    query = normalize(question)
    topics = {item.topic for item in passages if item.topic and item.topic in query}
    processing = bool(re.search(r"炮制|加工|饮片|切制|切片|处理|采收|采集|净制|干燥|蜜炙", query))
    overview = bool(re.fullmatch(r"(?:请|帮我)?(?:概括|总结)(?:当前)?资料(?:中的要点|的内容|要点|内容)?[。！？?]*", query))
    terms_query = query
    for word in QUESTION_WORDS:
        terms_query = terms_query.replace(word, " ")
    terms = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", terms_query)
    ranked = []
    for item in passages:
        text, name = normalize(item.text), normalize(item.source["name"])
        if topics:
            hit = item.topic in topics or any(topic in name or (not item.source.get("blocks") and topic in text) for topic in topics)
            score = 100 if hit else 0
            if processing and re.search(r"炮制|加工|饮片|采集|采收", item.title):
                if any(topic in text for topic in topics):
                    score = max(score, 140)
                elif re.search(r"方法|切制|修治", item.title):
                    score = max(score, 80)
                else:
                    score = max(score, 45)
        else:
            hit = bool(terms) and all(term in text or term in name for term in terms)
            score = sum(6 if term in normalize(item.title) else 2 for term in terms) if hit else 0
        if overview or score:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    if overview:
        selected, seen = [], set()
        for _, item in ranked:
            if item.source["id"] not in seen:
                selected.append(item)
                seen.add(item.source["id"])
        return selected[:3]
    return [item for _, item in ranked[:3]]


FIELD_QUESTIONS = (
    (r"功效|(?<!副)作用|应用|主治", {"功效", "应用"}),
    (r"性味|归经|药性", {"性味归经"}),
    (r"用法|用量|剂量|怎么用|如何用", {"用法用量"}),
    (r"禁忌|注意|慎用|禁用|不适合|副作用|不良反应", {"使用注意"}),
)


def focus_passage(question, text):
    """Keep requested fields and cautions from labeled herbal entries.

    Plain text stays intact. This narrows model context, while the source's
    fullText and blocks remain available for reading the complete original.
    """
    fields = {field for pattern, requested in FIELD_QUESTIONS if re.search(pattern, question) for field in requested}
    if not fields:
        return text
    lines = text.splitlines()
    labeled = [(line, re.match(r"^【([^】]+)】", line.strip())) for line in lines]
    # Do not drop an unstructured source or an entry without the requested field.
    if not any(match and match.group(1) in fields for _, match in labeled):
        return text
    fields.add("使用注意")
    return "\n".join(line for line, match in labeled if not match or match.group(1) in fields)
