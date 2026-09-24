from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.llm.protocols import ModelResult, ModelUsage
from app.llm.transport import (
    ModelEndpointError,
    build_http_client,
    raise_boundary_error,
    run_model_call,
)
from app.security.outbound_url import validate_outbound_url
from app.settings.service import LlmRuntime


def build_openai_client(runtime: LlmRuntime) -> OpenAI:
    return OpenAI(
        base_url=validate_outbound_url(runtime.base_url),
        api_key=runtime.api_key or "not-set",
        http_client=build_http_client(),
        max_retries=0,
    )


def _canonical_usage(response: Any) -> ModelUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return ModelUsage()
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(
        getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0
    )
    return ModelUsage(prompt_tokens, completion_tokens, total_tokens)


def complete_openai(
    runtime: LlmRuntime,
    system: str,
    user: str,
    json_mode: bool = False,
) -> ModelResult:
    try:
        client = build_openai_client(runtime)
        request: dict[str, Any] = {
            "model": runtime.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            request["response_format"] = {"type": "json_object"}
        response = run_model_call(
            client,
            lambda: client.chat.completions.create(**request),
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise ModelEndpointError("model_response_invalid")
        message = getattr(choices[0], "message", None)
        text = getattr(message, "content", None)
        if not isinstance(text, str) or not text.strip():
            raise ModelEndpointError("model_response_invalid")
        return ModelResult(text=text, usage=_canonical_usage(response))
    except Exception as exc:
        raise_boundary_error(exc)
