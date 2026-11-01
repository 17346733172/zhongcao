"""DeepSeek OpenAI-compatible JSON transport; no credentials in logs or responses."""
import json
import httpx
from fastapi import HTTPException
from pydantic import ValidationError


def request_json(settings, system_prompt, context, max_tokens=2048, timeout=30):
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=min(10, timeout)), follow_redirects=False) as client:
            response = client.post(settings.deepseek_base_url.rstrip("/") + "/chat/completions",
                                   headers={"Authorization": "Bearer " + settings.deepseek_api_key}, json=payload)
        if response.status_code in {401, 403}:
            raise HTTPException(503, "DeepSeek 鉴权失败，请联系管理员检查配置。")
        if response.status_code == 402:
            raise HTTPException(503, "DeepSeek 账户额度不足，请联系管理员。")
        if response.status_code == 429:
            raise HTTPException(429, "AI 服务请求繁忙，请稍后重试或切换原文检索。")
        if not 200 <= response.status_code < 300:
            raise HTTPException(502, "DeepSeek 服务暂时不可用，请重试或切换原文检索。")
        choice = response.json()["choices"][0]
        content = choice["message"]["content"]
        if choice.get("finish_reason") != "stop" or not isinstance(content, str) or not content.strip() or len(content) > 30000:
            raise ValueError("Incomplete model response")
        return content
    except httpx.TimeoutException:
        raise HTTPException(504, "AI 服务响应超时，请重试或切换原文检索。") from None
    except httpx.HTTPError:
        raise HTTPException(502, "暂时无法连接 DeepSeek，请重试或切换原文检索。") from None
    except (ValueError, KeyError, IndexError, TypeError, ValidationError):
        raise HTTPException(502, "AI 回答格式不完整，未作为有效回答保存，请重试。") from None
