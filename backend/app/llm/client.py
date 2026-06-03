import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.settings.service import LlmRuntime


def get_client(runtime: LlmRuntime | None = None) -> OpenAI:
    rt = runtime
    if rt is None:
        from app.settings.service import resolve_llm

        rt = resolve_llm()
    return OpenAI(base_url=rt.base_url, api_key=rt.api_key or "not-set")


def chat_json(
    system: str,
    user: str,
    schema_hint: str | None = None,
    *,
    runtime: LlmRuntime | None = None,
) -> dict[str, Any]:
    from app.settings.service import resolve_llm

    rt = runtime or resolve_llm()
    if rt.demo:
        return {}
    client = get_client(rt)
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": user + (f"\n\n请严格输出 JSON：\n{schema_hint}" if schema_hint else ""),
        },
    ]
    resp = client.chat.completions.create(
        model=rt.model,
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


def chat_text(system: str, user: str, *, runtime: LlmRuntime | None = None) -> str:
    from app.settings.service import resolve_llm

    rt = runtime or resolve_llm()
    if rt.demo:
        return "（Demo 模式）已收到你的消息。请在「设置」中配置模型 API Key。"
    client = get_client(rt)
    resp = client.chat.completions.create(
        model=rt.model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""
