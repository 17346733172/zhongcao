"""DeepSeek generation grounded in server-retrieved passages, with checked citations."""
import json
from collections import OrderedDict
from hashlib import sha256
import re
from time import perf_counter
from threading import BoundedSemaphore, RLock
from typing import Literal
import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from .rag import CODE_ROOT
from RAG.prompt import SYSTEM_PROMPT, GENERAL_SYSTEM_PROMPT
from RAG.llm import request_json
from .retrieval import focus_passage, retrieve
from .conversation_context import resolve_question, topic_lookup
from .question_understanding import (UNDERSTANDING_PROMPT, UnderstoodQuestion, should_understand,
                                     understanding_context, resolve_understanding)



class GeneralSection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("title", "content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Blank model section")
        return value.strip()


class GeneratedSection(GeneralSection):
    origin: Literal["document", "ai_supplement"]
    citations: list[int] = Field(max_length=3)


class GeneralAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=120)
    sections: list[GeneralSection] = Field(min_length=1, max_length=6)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value):
        if not value.strip():
            raise ValueError("Blank model title")
        return value.strip()


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answerable: bool
    title: str = Field(min_length=1, max_length=120)
    sections: list[GeneratedSection] = Field(max_length=6)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value):
        if not value.strip():
            raise ValueError("Blank model title")
        return value.strip()


def no_match(insufficient=False):
    return {
        "title": "资料不足以回答这个问题" if insufficient else "未找到相关内容",
        "introduction": "当前知识库没有足够的相关原文，请尝试其他药材名称或关键词。",
        "sections": [], "sources": [], "mode": "no_match",
    }




def request_completion(settings, materials, question, history=None, resolved_question=None):
    content = request_json(settings, SYSTEM_PROMPT, {
        "question": question, "resolved_question": resolved_question or question,
        "conversation_history": history or [], "reference_material": materials,
    })
    try:
        return GeneratedAnswer.model_validate_json(content)
    except (ValueError, ValidationError):
        raise HTTPException(502, "AI 回答格式不完整，未作为有效回答保存，请重试。") from None


def request_understanding(settings, question, history, documents, reference):
    content = request_json(settings, UNDERSTANDING_PROMPT,
                           understanding_context(question, history, documents, reference),
                           max_tokens=512, timeout=10)
    try:
        understood = UnderstoodQuestion.model_validate_json(content)
        return resolve_understanding(understood, history, documents, reference)
    except (ValueError, ValidationError):
        raise HTTPException(502, "AI 未能准确理解这条问题，请补充药材名称或换种说法重试。") from None


def clarification(message):
    return {"title": "请补充问题的主题", "introduction": message,
            "sections": [], "sources": [], "mode": "clarification"}


def measure(timings, name, function, *args):
    started = perf_counter()
    try:
        return function(*args)
    finally:
        if timings is not None:
            timings[name] = timings.get(name, 0) + (perf_counter() - started) * 1000


class ChatService:
    def __init__(self, settings, retriever=None):
        self.settings = settings
        self.retriever = retriever
        self.slots = BoundedSemaphore(4)
        self.answer_cache = OrderedDict()
        self.answer_cache_lock = RLock()

    def retrieve(self, question, documents, reference):
        if self.retriever is not None:
            return self.retriever.retrieve(question, documents, reference)
        return retrieve(question, documents, reference)

    def answer_general(self, question, history=None, timings=None):
        if not self.settings.deepseek_api_key:
            raise HTTPException(503, "AI 服务尚未配置，请联系管理员。")
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, "AI 服务请求繁忙，请稍后重试。")
        try:
            content = measure(timings, "generation", request_json, self.settings, GENERAL_SYSTEM_PROMPT, {
                "question": question, "conversation_history": history or [],
            })
            try:
                generated = GeneralAnswer.model_validate_json(content)
            except (ValueError, ValidationError):
                raise HTTPException(502, "AI 回答格式不完整，未作为有效回答保存，请重试。") from None
            return {
                "title": generated.title, "introduction": "",
                "sections": [section.model_dump() for section in generated.sections],
                "sources": [], "mode": "generated", "model": self.settings.deepseek_model,
            }
        finally:
            self.slots.release()

    def answer(self, question, documents, reference, history=None, timings=None, cache_scope=None):
        history = history or []
        passages = []

        def result(payload):
            if self.retriever is not None:
                payload.update(retrievalMethod=getattr(self.retriever, "method", "vector"), retrievedSources=[
                    {**item.source, "id": item.source["id"] + "-" + str(item.index),
                     "excerpt": item.text, "demo": False} for item in passages
                ])
            return payload

        resolution = measure(timings, "context", resolve_question, question, history, documents, reference)
        if resolution.clarification:
            return clarification(resolution.clarification)
        understand_first = (self.retriever is not None and history and resolution.question == question
                            and not topic_lookup(documents, reference)(question)
                            and should_understand(question, resolution, []))
        # Omitted subjects / typos need interpretation anyway. Do it before an
        # otherwise wasted vector pass, then retrieve once using the resolved query.
        if not understand_first:
            passages = measure(timings, "retrieval", self.retrieve, resolution.question, documents, reference)
        needs_understanding = understand_first or should_understand(question, resolution, passages)
        # Numeric/noise inputs still never call a model or reuse old subjects.
        if not passages and not needs_understanding:
            return result(no_match())
        if not self.settings.deepseek_api_key:
            raise HTTPException(503, "AI 服务尚未配置，请联系管理员或使用原文检索。")
        if not self.slots.acquire(blocking=False):
            raise HTTPException(429, "AI 服务请求繁忙，请稍后重试。")
        try:
            if needs_understanding:
                resolution = measure(timings, "understanding", request_understanding, self.settings, question, history, documents, reference)
                if resolution.clarification:
                    return clarification(resolution.clarification)
                if not resolution.question:
                    return result(no_match())
                passages = measure(timings, "retrieval", self.retrieve, resolution.question, documents, reference)
                # Understanding a question is not evidence; retry actual retrieval.
                if not passages:
                    return result(no_match())
            materials = [{"id": i + 1, "document": item.source["name"], "section": item.title, "text": focus_passage(resolution.question, item.text)[:3000]} for i, item in enumerate(passages)]
            cache_key, generated, cache_hit = None, None, False
            if (self.retriever is not None and cache_scope is not None
                    and self.settings.rag_answer_cache_size and self.settings.rag_answer_cache_seconds):
                source_versions = [sha256(item.source["fullText"].encode()).hexdigest() for item in passages]
                cache_key = sha256(json.dumps([cache_scope, question, resolution.question, history, materials, source_versions],
                                               ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                with self.answer_cache_lock:
                    cached = self.answer_cache.get(cache_key)
                    if cached and cached[0] > perf_counter():
                        generated = GeneratedAnswer.model_validate_json(cached[1])
                        cache_hit = True
                        self.answer_cache.move_to_end(cache_key)
                        if timings is not None:
                            timings["answer_cache"] = 0
                    elif cached:
                        del self.answer_cache[cache_key]
            if generated is None:
                generated = measure(timings, "generation", request_completion, self.settings, materials, question, history, resolution.question)
            if not generated.answerable:
                return result(no_match(insufficient=True))
            if not generated.sections:
                raise HTTPException(502, "AI 回答缺少正文，请重试。")
            for section in generated.sections:
                if section.origin == "document" and not section.citations:
                    raise HTTPException(502, "资料回答缺少原文引用，请重试。")
                if section.origin == "ai_supplement" and section.citations:
                    raise HTTPException(502, "AI 补充不能标作文档引用，请重试。")
            used = sorted({citation for section in generated.sections for citation in section.citations})
            if any(citation < 1 or citation > len(passages) for citation in used):
                raise HTTPException(502, "AI 回答引用了无效来源，未作为有效回答保存，请重试。")
            if any(re.search(r"\[\s*\d+\s*\]", section.content) for section in generated.sections):
                raise HTTPException(502, "AI 回答包含未校验的引用标记，请重试。")
            if cache_key is not None and not cache_hit:
                with self.answer_cache_lock:
                    self.answer_cache[cache_key] = (perf_counter() + self.settings.rag_answer_cache_seconds,
                                                    generated.model_dump_json())
                    self.answer_cache.move_to_end(cache_key)
                    while len(self.answer_cache) > self.settings.rag_answer_cache_size:
                        self.answer_cache.popitem(last=False)
            indices = {citation: index for index, citation in enumerate(used)}
            sources = []
            for citation in used:
                passage = passages[citation - 1]
                sources.append({**passage.source, "id": passage.source["id"] + "-" + str(passage.index), "excerpt": materials[citation - 1]["text"], "demo": False})
            return result({
                "title": generated.title,
                "introduction": (("我理解你是在问：" + resolution.question.rstrip("。！？?!") + "。") if needs_understanding else "")
                                + "以下回答由 DeepSeek 生成。资料依据附原文引用；AI 补充单独标注为非文档原文，供参考并需核实。",
                "sections": [{"title": section.title, "content": section.content, "origin": section.origin,
                              **({"sourceIndex": indices[section.citations[0]]} if section.citations else {}),
                              "sourceIndices": list(dict.fromkeys(indices[citation] for citation in section.citations))}
                             for section in generated.sections],
                "sources": sources, "mode": "generated", "model": self.settings.deepseek_model,
                "resolvedQuestion": resolution.question,
            })
        finally:
            self.slots.release()
