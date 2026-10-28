"""Resolve short follow-up questions using bounded, untrusted conversation context."""
from dataclasses import dataclass
import re
from .retrieval import normalize, passages_for, retrieve


FOLLOW_UP_WORDS = sorted({
    "作用", "功效", "性味", "归经", "药性", "用法用量", "用法", "用量", "剂量", "禁忌", "副作用", "不良反应",
    "注意事项", "使用注意", "注意", "炮制", "处理", "加工", "方法", "泡水", "煎服", "煎煮", "服用", "有毒", "安全",
    "有什么", "有哪些", "是什么", "为什么", "怎么样", "怎么", "如何", "多少", "多久", "几次", "一天", "可以", "是否", "能不能", "能", "吗", "呢", "啊", "的", "和", "与", "及", "那", "请问", "请", "再", "详细一点", "详细", "解释", "说说", "继续", "展开", "还有",
}, key=len, reverse=True)
PRONOUN = re.compile(r"它们|它|这个药|这味药|那味药|这种药|上面|刚才|前面|两者|二者|这两个")


@dataclass(frozen=True)
class Resolution:
    question: str
    clarification: str = ""


def depends_on_context(question):
    text = normalize(question)
    text = re.sub(r"[\s？?！!。，,、：:；;]", "", text)
    if not text or re.search(r"[a-z0-9_]", text) or len(text) > 180:
        return False
    if PRONOUN.search(text):
        return True
    remaining = text
    for word in FOLLOW_UP_WORDS:
        remaining = remaining.replace(word, "")
    return not remaining


def topic_lookup(documents, reference):
    sources = [reference] if reference else []
    sources += [{"name": doc["name"], "fullText": doc.get("content", "")} for doc in documents]
    catalog = {item.topic for source in sources for item in passages_for(source) if item.topic}

    def topics_in(text):
        found = [topic for topic in catalog if topic in normalize(text)]
        found = [topic for topic in found if not any(topic != other and topic in other for other in found)]
        return sorted(found, key=lambda topic: normalize(text).find(topic))

    return topics_in


def previous_subject(history, documents, reference):
    topics_in = topic_lookup(documents, reference)
    for turn in reversed(history):
        previous = turn["question"]
        topics = topics_in(previous)
        if topics:
            return topics, previous
        if not depends_on_context(previous) and retrieve(previous, documents, reference):
            return [], previous
    return [], ""


def resolve_question(question, history, documents, reference):
    topics_in = topic_lookup(documents, reference)
    explicit = topics_in(question)
    comparison = bool(re.search(r"区别|不同|相同|一样|相比|比较|比起来", question))
    omitted_comparison = comparison and (PRONOUN.search(question) or re.match(r"^(?:那)?(?:和|与|跟|比)", question.strip()))
    if explicit and not omitted_comparison:
        return Resolution(question)
    if not omitted_comparison and not depends_on_context(question):
        return Resolution(question)

    previous_topics, previous_question = previous_subject(history, documents, reference)
    if not previous_question:
        return Resolution(question, "请先说明要查询的药材或资料主题，例如先输入药材名称，再追问作用、用法或注意事项。")
    if omitted_comparison:
        previous_topics = [topic for topic in previous_topics if topic not in explicit]
        if not previous_topics:
            return Resolution(question, "你想比较哪两种药材？请补充另一种药材名称。")
    singular = bool(re.search(r"它(?!们)|这个药|这味药|那味药|这种药", question))
    if len(previous_topics) > 1 and singular and not re.search(r"它们|两者|二者|这两个|分别", question):
        return Resolution(question, "你指的是" + "、".join(previous_topics[:3]) + "中的哪一种？请说明药材名称。")
    topic_text = "、".join(previous_topics) if previous_topics else previous_question
    return Resolution(topic_text + "：" + question)
