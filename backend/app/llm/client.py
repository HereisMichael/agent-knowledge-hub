from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.config import settings
from app.llm import anthropic_messages, openai_chat
from app.llm.protocols import (
    ANTHROPIC_MESSAGES,
    OPENAI_CHAT,
    ModelResult,
    ModelUsage,
)
from app.llm.transport import ModelEndpointError
from app.observability import current_request_id
from app.settings.service import LlmRuntime


_FENCED_JSON_OBJECT = re.compile(
    r"\A\s*\x60{3}(?:json)?[ \t]*\r?\n(?P<body>.*?)"
    r"\r?\n\x60{3}[ \t]*\s*\Z",
    re.IGNORECASE | re.DOTALL,
)


def parse_json_object(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ModelEndpointError("model_json_invalid")
    match = _FENCED_JSON_OBJECT.fullmatch(text)
    candidate = match.group("body") if match is not None else text

    def reject_non_finite(_constant: str) -> None:
        raise ValueError("non-finite JSON number")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON object key")
            value[key] = item
        return value

    try:
        value = json.loads(
            candidate,
            parse_constant=reject_non_finite,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (TypeError, ValueError):
        raise ModelEndpointError("model_json_invalid") from None
    if not isinstance(value, dict):
        raise ModelEndpointError("model_json_invalid")
    return value


def record_model_usage(usage: ModelUsage, *, model: str) -> None:
    over_threshold = usage.total_tokens >= settings.model_token_alert_threshold
    logging.getLogger("akh.model").log(
        logging.WARNING if over_threshold else logging.INFO,
        "model_token_threshold_exceeded" if over_threshold else "model_usage",
        extra={
            "request_id": current_request_id(),
            "model": model,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
    )


def _complete(
    runtime: LlmRuntime,
    system: str,
    user: str,
    *,
    json_mode: bool,
) -> ModelResult:
    if runtime.protocol == OPENAI_CHAT:
        return openai_chat.complete_openai(
            runtime,
            system,
            user,
            json_mode=json_mode,
        )
    if runtime.protocol == ANTHROPIC_MESSAGES:
        return anthropic_messages.complete_anthropic(
            runtime,
            system,
            user,
            json_mode=json_mode,
        )
    raise ModelEndpointError("model_protocol_unsupported")


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
    prompt = user + (f"\n\n请严格输出 JSON：\n{schema_hint}" if schema_hint else "")
    result = _complete(rt, system, prompt, json_mode=True)
    record_model_usage(result.usage, model=rt.model)
    return parse_json_object(result.text)


def chat_text(system: str, user: str, *, runtime: LlmRuntime | None = None) -> str:
    from app.settings.service import resolve_llm

    rt = runtime or resolve_llm()
    if rt.demo:
        return "（Demo 模式）已收到你的消息。请在「设置」中配置模型 API Key。"
    result = _complete(rt, system, user, json_mode=False)
    record_model_usage(result.usage, model=rt.model)
    return result.text
