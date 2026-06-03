"""Per-user LLM settings overlay."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.db import store


@dataclass
class LlmRuntime:
    base_url: str
    api_key: str
    model: str
    demo: bool


def mask_api_key(key: str) -> str:
    k = (key or "").strip()
    if not k or len(k) < 8:
        return ""
    return f"{k[:3]}…{k[-4:]}"


def resolve_llm(user_id: str = "default") -> LlmRuntime:
    row = store.get_user_settings(user_id)
    base_url = (row.get("llm_base_url") or "").strip() or settings.llm_base_url
    api_key = (row.get("llm_api_key") or "").strip() or settings.llm_api_key
    model = (row.get("llm_model") or "").strip() or settings.llm_model
    force_demo = bool(row.get("force_demo"))

    if force_demo:
        demo = True
    elif row.get("llm_api_key"):
        demo = not api_key or api_key in ("your_api_key_here", "not-set", "sk-xxx")
    else:
        demo = settings.use_demo_llm

    return LlmRuntime(base_url=base_url, api_key=api_key or "not-set", model=model, demo=demo)


def get_settings_public(user_id: str = "default") -> dict:
    row = store.get_user_settings(user_id)
    runtime = resolve_llm(user_id)
    return {
        "llm_base_url": row.get("llm_base_url") or settings.llm_base_url,
        "llm_model": row.get("llm_model") or settings.llm_model,
        "llm_api_key_masked": mask_api_key(row.get("llm_api_key") or settings.llm_api_key),
        "has_custom_key": bool((row.get("llm_api_key") or "").strip()),
        "force_demo": bool(row.get("force_demo")),
        "demo_mode_active": runtime.demo,
        "using_server_env_fallback": not (row.get("llm_api_key") or "").strip(),
    }


def update_settings(user_id: str, payload: dict) -> dict:
    store.upsert_user_settings(user_id, payload)
    return get_settings_public(user_id)
