from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.db import store
from app.main import app


def _configure(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "authorization.db"))
    monkeypatch.setattr(settings, "auth_invite_code", "invite-2026-safe")
    monkeypatch.setattr(settings, "session_cookie_name", "akh_session")
    monkeypatch.setattr(settings, "session_ttl_hours", 24)
    monkeypatch.setattr(settings, "app_env", "development")
    store.init_db()


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "invite_code": "invite-2026-safe",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def test_training_routes_require_authentication(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    anonymous = TestClient(app)

    response = anonymous.get("/api/questions/all")

    assert response.status_code == 401
    assert response.json()["detail"] == "authentication_required"


def test_query_user_id_cannot_select_another_users_settings(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    member = TestClient(app)
    owner_user = _register(owner, "owner@example.com")
    member_user = _register(member, "member@example.com")
    owner.put("/api/settings", json={"llm_model": "owner-model", "force_demo": True})
    member.put("/api/settings", json={"llm_model": "member-model", "force_demo": True})

    response = owner.get(f"/api/settings?user_id={member_user['id']}")

    assert response.status_code == 200
    assert response.json()["llm_model"] == "owner-model"
    assert owner_user["id"] != member_user["id"]


def test_unsafe_model_endpoint_returns_a_stable_validation_error(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    _register(owner, "owner@example.com")

    response = owner.put(
        "/api/settings",
        json={
            "llm_base_url": "http://169.254.169.254/latest/meta-data",
            "force_demo": True,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "unsafe_llm_base_url"
    assert store.get_user_settings(
        store.get_user_by_email("owner@example.com")["id"]
    ).get("llm_base_url") is None


def test_custom_endpoint_without_a_new_key_is_rejected(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    _register(owner, "owner@example.com")
    from app.security import outbound_url

    monkeypatch.setattr(
        outbound_url.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (
                2,
                1,
                6,
                "",
                ("93.184.216.34", 443),
            )
        ],
    )

    response = owner.put(
        "/api/settings",
        json={
            "llm_base_url": "https://custom.example/v1",
            "force_demo": False,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "model_key_required_for_endpoint"


def test_connection_test_reports_real_protocol(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    _register(owner, "owner@example.com")
    from app.settings.service import LlmRuntime

    monkeypatch.setattr(
        "app.settings.service.resolve_llm",
        lambda user_id: LlmRuntime(
            protocol="anthropic_messages",
            base_url="https://api.anthropic.com",
            api_key="secret",
            model="claude-test",
            demo=False,
        ),
    )
    monkeypatch.setattr("app.llm.client.chat_text", lambda *args, **kwargs: "ok")

    response = owner.post("/api/settings/test")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "code": "connected",
        "message": "\u8fde\u63a5\u6210\u529f",
        "protocol": "anthropic_messages",
        "model": "claude-test",
        "preview": "ok",
    }


def test_connection_test_demo_reports_no_external_request(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    _register(owner, "owner@example.com")
    from app.settings.service import LlmRuntime

    monkeypatch.setattr(
        "app.settings.service.resolve_llm",
        lambda user_id: LlmRuntime(
            protocol="openai_chat",
            base_url="https://api.openai.com/v1",
            api_key="",
            model="demo-model",
            demo=True,
        ),
    )

    def unexpected_call(*args, **kwargs):
        raise AssertionError("model call should not run in demo mode")

    monkeypatch.setattr("app.llm.client.chat_text", unexpected_call)

    response = owner.post("/api/settings/test")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "code": "demo_mode_active",
        "message": "\u5f53\u524d\u4e3a Demo \u6a21\u5f0f\uff0c\u672a\u5411\u5916\u90e8\u6a21\u578b\u670d\u52a1\u53d1\u8d77\u8bf7\u6c42",
        "protocol": "openai_chat",
        "model": "demo-model",
    }


def test_connection_test_auth_failure_is_safe_and_actionable(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app, raise_server_exceptions=False)
    _register(owner, "owner@example.com")
    from app.llm import client as llm_client
    from app.settings.service import LlmRuntime

    monkeypatch.setattr(
        "app.settings.service.resolve_llm",
        lambda user_id: LlmRuntime(
            base_url="https://api.example.com/v1",
            api_key="sk-auth-secret",
            model="test-model",
            demo=False,
        ),
    )

    def authentication_failed(*args, **kwargs):
        raise llm_client.ModelEndpointError("model_auth_failed")

    monkeypatch.setattr(llm_client, "chat_text", authentication_failed)

    response = owner.post("/api/settings/test")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "code": "model_auth_failed",
        "message": "\u8ba4\u8bc1\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5 API Key",
        "protocol": "openai_chat",
        "model": "test-model",
    }
    assert "sk-auth-secret" not in response.text
    assert "api.example.com" not in response.text


def test_connection_test_unknown_model_failure_does_not_leak_details(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    _register(owner, "owner@example.com")
    from app.llm import client as llm_client
    from app.settings.service import LlmRuntime

    monkeypatch.setattr(
        "app.settings.service.resolve_llm",
        lambda user_id: LlmRuntime(
            base_url="https://private.example/v1",
            api_key="sk-unknown-secret",
            model="test-model",
            demo=False,
        ),
    )
    monkeypatch.setattr(
        llm_client,
        "chat_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            llm_client.ModelEndpointError("provider_details: sk-unknown-secret")
        ),
    )

    response = owner.post("/api/settings/test")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "code": "model_endpoint_unreachable",
        "message": "\u65e0\u6cd5\u8fde\u63a5\u6a21\u578b\u670d\u52a1",
        "protocol": "openai_chat",
        "model": "test-model",
    }
    assert "sk-unknown-secret" not in response.text
    assert "private.example" not in response.text

def test_connection_test_runtime_resolution_failure_is_safe(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app, raise_server_exceptions=False)
    _register(owner, "owner@example.com")
    sentinel = "sk-resolve-sentinel https://secret.example/v1 response-body-sentinel"

    def cannot_resolve_runtime(user_id):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(
        "app.settings.service.resolve_llm",
        cannot_resolve_runtime,
    )

    response = owner.post("/api/settings/test")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "code": "model_endpoint_unreachable",
        "message": "\u65e0\u6cd5\u8fde\u63a5\u6a21\u578b\u670d\u52a1",
        "protocol": "",
        "model": "",
    }
    assert sentinel not in response.text
    assert "secret.example" not in response.text


def test_connection_test_unexpected_model_failure_does_not_leak_details(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    _register(owner, "owner@example.com")
    from app.settings.service import LlmRuntime

    sentinel = "sk-call-sentinel https://secret.example/v1 response-body-sentinel"
    monkeypatch.setattr(
        "app.settings.service.resolve_llm",
        lambda user_id: LlmRuntime(
            base_url="https://private.example/v1",
            api_key="sk-call-secret",
            model="test-model",
            demo=False,
        ),
    )

    def unexpected_failure(*args, **kwargs):
        raise RuntimeError(sentinel)

    monkeypatch.setattr("app.llm.client.chat_text", unexpected_failure)

    response = owner.post("/api/settings/test")

    assert response.status_code == 200
    assert response.json() == {
        "ok": False,
        "code": "model_endpoint_unreachable",
        "message": "\u65e0\u6cd5\u8fde\u63a5\u6a21\u578b\u670d\u52a1",
        "protocol": "openai_chat",
        "model": "test-model",
    }
    assert sentinel not in response.text
    assert "secret.example" not in response.text
    assert "sk-call-secret" not in response.text

def test_mock_session_is_invisible_to_another_user(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    stranger = TestClient(app)
    _register(owner, "owner@example.com")
    _register(stranger, "stranger@example.com")
    created = owner.post(
        "/api/mock/sessions",
        json={"mode": "free", "vendor": "aliyun", "focus": "architecture"},
    )
    session_id = created.json()["id"]

    response = stranger.get(f"/api/mock/sessions/{session_id}")

    assert response.status_code == 404


def test_admin_routes_use_role_and_reject_legacy_header(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    admin = TestClient(app)
    member = TestClient(app)
    anonymous = TestClient(app)
    _register(admin, "owner@example.com")
    _register(member, "member@example.com")

    assert admin.get("/api/admin/content/pending").status_code == 200
    member_response = member.get("/api/admin/content/pending")
    assert member_response.status_code == 403
    assert member_response.json()["detail"] == "admin_required"
    assert anonymous.get(
        "/api/admin/content/pending",
        headers={"X-Admin-Key": "change-me-admin-key"},
    ).status_code == 401


def test_first_admin_claims_legacy_default_user_data_once(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    store.upsert_user_settings(
        "default",
        {"llm_model": "legacy-model", "force_demo": 1},
    )
    first = TestClient(app)
    second = TestClient(app)

    admin_user = _register(first, "owner@example.com")
    member_user = _register(second, "member@example.com")

    assert store.get_user_settings(admin_user["id"])["llm_model"] == "legacy-model"
    assert store.get_user_settings("default") == {"user_id": "default"}
    assert store.get_user_settings(member_user["id"]) == {"user_id": member_user["id"]}


def test_settings_api_persists_and_returns_public_protocol_only(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    monkeypatch.setattr(
        settings, "credential_encryption_key", "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
    )
    owner = TestClient(app)
    _register(owner, "owner@example.com")
    from app.security import outbound_url

    monkeypatch.setattr(
        outbound_url.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    secret = "sk-api-protocol-secret"
    saved = owner.put(
        "/api/settings",
        json={
            "llm_api_key": secret,
            "llm_base_url": "https://staging.example/v1",
            "llm_protocol": "anthropic_messages",
            "force_demo": True,
        },
    )
    loaded = owner.get("/api/settings")

    assert saved.status_code == 200
    assert loaded.status_code == 200
    for response in (saved, loaded):
        body = response.json()
        assert body["llm_protocol"] == "anthropic_messages"
        assert "llm_api_key" not in body
        assert secret not in response.text
        assert not {"llm_api_key_ciphertext", "llm_api_key_nonce", "llm_api_key_audience"} & body.keys()


def test_settings_api_rejects_unsupported_protocol_without_persistence(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    owner = TestClient(app)
    user = _register(owner, "owner@example.com")

    response = owner.put(
        "/api/settings",
        json={"llm_protocol": "responses_api", "force_demo": True},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "unsupported_llm_protocol"
    assert store.get_user_settings(user["id"]) == {"user_id": user["id"]}
