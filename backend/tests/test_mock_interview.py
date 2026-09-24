from __future__ import annotations

from app.config import settings
from app.db import store
from app.interview import mock as mock_service
from app.settings.service import LlmRuntime


def _create_session(tmp_path, monkeypatch, user_id: str = "session-owner") -> dict:
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "mock-interview.db"))
    store.init_db()
    return store.create_mock_session("free", "aliyun", "architecture", user_id)


def test_finish_uses_non_demo_user_runtime_when_global_demo_is_active(
    tmp_path,
    monkeypatch,
):
    session = _create_session(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "demo_mode", True)
    runtime = LlmRuntime(
        protocol="anthropic_messages",
        base_url="https://api.anthropic.com",
        api_key="sk-user-key",
        model="claude-user",
        demo=False,
    )
    resolved_for = []

    def resolve(user_id):
        resolved_for.append(user_id)
        return runtime

    def complete(system, user, *, runtime):
        assert runtime is expected_runtime
        return {
            "scores": {"structure": 91},
            "highlights": ["provider-report"],
            "gaps": [],
            "answer_rewrite": "provider rewrite",
            "suggested_lab_ids": [],
        }

    expected_runtime = runtime
    monkeypatch.setattr(mock_service, "resolve_llm", resolve)
    monkeypatch.setattr(mock_service, "chat_json", complete)
    monkeypatch.setattr(mock_service, "recommend_labs", lambda **kwargs: [])

    finished = mock_service.finish_session(session["id"], "session-owner")

    assert resolved_for == ["session-owner"]
    assert finished["report"] == {
        "scores": {"structure": 91},
        "highlights": ["provider-report"],
        "gaps": [],
        "answer_rewrite": "provider rewrite",
        "suggested_lab_ids": [],
        "recommended_labs": [],
    }


def test_finish_uses_complete_demo_report_for_user_forced_demo(
    tmp_path,
    monkeypatch,
):
    session = _create_session(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "llm_api_key", "sk-global-key")
    runtime = LlmRuntime(
        protocol="openai_chat",
        base_url="https://api.openai.com/v1",
        api_key="not-set",
        model="gpt-demo",
        demo=True,
    )
    resolved_for = []

    def resolve(user_id):
        resolved_for.append(user_id)
        return runtime

    def forbidden_chat(*args, **kwargs):
        raise AssertionError("forced Demo must not call a provider")

    monkeypatch.setattr(mock_service, "resolve_llm", resolve)
    monkeypatch.setattr(mock_service, "chat_json", forbidden_chat)
    monkeypatch.setattr(mock_service, "recommend_labs", lambda **kwargs: [])

    finished = mock_service.finish_session(session["id"], "session-owner")

    assert resolved_for == ["session-owner"]
    assert finished["report"] == {
        "scores": {"structure": 75, "depth": 70, "communication": 78},
        "highlights": ["表达较清晰", "有项目经历"],
        "gaps": ["架构量化指标可加强", "竞品对比不够"],
        "answer_rewrite": "建议在架构题中补充 RPO/RTO 与成本估算。",
        "suggested_lab_ids": [
            "lab-draw-arch-mermaid",
            "lab-vendor-slb-compare",
        ],
        "recommended_labs": [],
    }
