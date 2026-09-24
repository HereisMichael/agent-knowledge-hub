from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.llm.protocols import ModelResult, ModelUsage
from app.llm.transport import (
    ModelEndpointError,
    build_http_client,
    model_error_code_for_status,
    raise_boundary_error,
    run_model_call,
)
from app.security.outbound_url import validate_outbound_url
from app.settings.service import LlmRuntime


ANTHROPIC_VERSION = "2023-06-01"
JSON_ONLY_INSTRUCTION = (
    "请只输出一个有效的 JSON 对象，不要添加解释、Markdown 代码围栏或其他内容。"
)


def anthropic_messages_url(base_url: str) -> str:
    validated = validate_outbound_url(base_url)
    parts = urlsplit(validated)
    path = parts.path.rstrip("/")
    if path == "/v1" or path.endswith("/v1"):
        target_path = path + "/messages"
    else:
        target_path = path + "/v1/messages"
    return urlunsplit(
        (parts.scheme, parts.netloc, target_path, parts.query, parts.fragment)
    )


def _token_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ModelEndpointError("model_response_invalid")
    return value


def _decode_anthropic_response(body: Any) -> ModelResult:
    if not isinstance(body, dict):
        raise ModelEndpointError("model_response_invalid")

    content = body.get("content")
    usage = body.get("usage")
    if not isinstance(content, list) or not isinstance(usage, dict):
        raise ModelEndpointError("model_response_invalid")

    text_parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            raise ModelEndpointError("model_response_invalid")
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if not isinstance(text, str):
            raise ModelEndpointError("model_response_invalid")
        text_parts.append(text)

    text = "".join(text_parts)
    if not text.strip():
        raise ModelEndpointError("model_response_invalid")

    prompt_tokens = _token_count(usage.get("input_tokens"))
    completion_tokens = _token_count(usage.get("output_tokens"))
    return ModelResult(
        text=text,
        usage=ModelUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


def complete_anthropic(
    runtime: LlmRuntime,
    system: str,
    user: str,
    json_mode: bool = False,
) -> ModelResult:
    try:
        url = anthropic_messages_url(runtime.base_url)
        client = build_http_client()
        user_prompt = (
            user + "\n\n" + JSON_ONLY_INSTRUCTION if json_mode else user
        )
        payload = {
            "model": runtime.model,
            "max_tokens": 2048,
            "temperature": 0.2,
            "system": system,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": runtime.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        def request_and_decode() -> ModelResult:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                raise ModelEndpointError(
                    model_error_code_for_status(response.status_code)
                )
            try:
                body = response.json()
            except (TypeError, UnicodeError, ValueError):
                raise ModelEndpointError("model_response_invalid") from None
            return _decode_anthropic_response(body)

        return run_model_call(client, request_and_decode)
    except Exception as exc:
        raise_boundary_error(exc)
