import json
from typing import Any

from openai import OpenAI

from app.config import settings


def get_client() -> OpenAI:
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "not-set",
    )


def chat_json(system: str, user: str, schema_hint: str | None = None) -> dict[str, Any]:
    if settings.use_demo_llm:
        return {"answer": "（Demo 模式）请配置 LLM_API_KEY 以启用完整 AI 能力。", "citations": []}
    client = get_client()
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": user + (f"\n\n请严格输出 JSON：\n{schema_hint}" if schema_hint else ""),
        },
    ]
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


def chat_text(system: str, user: str) -> str:
    if settings.use_demo_llm:
        return "（Demo 模式）已收到你的消息。配置 LLM_API_KEY 后可获得完整模拟面试与 AI 评分。"
    client = get_client()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""
