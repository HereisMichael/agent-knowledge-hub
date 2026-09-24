from __future__ import annotations

from dataclasses import dataclass


OPENAI_CHAT = "openai_chat"
ANTHROPIC_MESSAGES = "anthropic_messages"
SUPPORTED_PROTOCOLS = frozenset({OPENAI_CHAT, ANTHROPIC_MESSAGES})


@dataclass(frozen=True)
class ModelUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ModelResult:
    text: str
    usage: ModelUsage
