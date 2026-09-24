import base64
import binascii
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


SUPPORTED_LLM_PROTOCOLS = frozenset({"openai_chat", "anthropic_messages"})


def normalize_llm_protocol(value: str | None) -> str:
    protocol = (value or "openai_chat").strip().lower()
    if protocol not in SUPPORTED_LLM_PROTOCOLS:
        raise ValueError("unsupported_llm_protocol")
    return protocol


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_base_url: str = "https://api.cursor.com/v1"
    llm_api_key: str = ""
    llm_model: str = "composer-2.5"
    llm_protocol: str = "openai_chat"
    demo_mode: bool = False

    app_env: str = "development"
    auth_invite_code: str = ""
    session_cookie_name: str = "akh_session"
    session_ttl_hours: int = 168
    credential_encryption_key: str = ""
    backup_signing_key: str = ""
    cors_allowed_origins: str = ""
    slow_request_ms: int = 2000
    model_token_alert_threshold: int = 20000

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    chroma_path: str = "./data/chroma"
    sqlite_path: str = "./data/hub.db"
    backup_path: str = "./data/backups"
    privacy_ledger_path: str = "./data/privacy-deletions.db"
    privacy_ledger_id: str = "development-ledger"
    knowledge_path: str = "../knowledge"
    ingest_extra_dirs: str = ""

    content_update_cron: str = "0 6 * * *"
    content_tz: str = "Asia/Shanghai"
    auto_publish_trusted: bool = False
    auto_publish_min_score: float = 85.0
    content_scheduler_enabled: bool = True

    content_root: str = "../content"
    project_root: str = ".."

    @property
    def use_demo_llm(self) -> bool:
        if self.demo_mode:
            return True
        key = (self.llm_api_key or "").strip()
        return not key or key in ("your_api_key_here", "not-set", "sk-xxx")

    @property
    def knowledge_dir(self) -> Path:
        return Path(self.knowledge_path).resolve()

    @property
    def content_dir(self) -> Path:
        return Path(self.content_root).resolve()

    @property
    def extra_knowledge_dirs(self) -> list[Path]:
        if not self.ingest_extra_dirs.strip():
            return []
        return [Path(p.strip()).resolve() for p in self.ingest_extra_dirs.split(",") if p.strip()]

    @property
    def cors_origins(self) -> list[str]:
        configured = [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]
        if configured:
            return configured
        if self.app_env in {"development", "test"}:
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
            ]
        return []

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        environment = self.app_env.strip().lower()
        if environment not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production")
        self.llm_protocol = normalize_llm_protocol(self.llm_protocol)
        if self.session_ttl_hours < 1 or self.session_ttl_hours > 720:
            raise ValueError("SESSION_TTL_HOURS must be between 1 and 720")
        if self.slow_request_ms < 10 or self.slow_request_ms > 600_000:
            raise ValueError("SLOW_REQUEST_MS must be between 10 and 600000")
        if self.model_token_alert_threshold < 1:
            raise ValueError("MODEL_TOKEN_ALERT_THRESHOLD must be positive")
        if Path(self.sqlite_path).resolve() == Path(
            self.privacy_ledger_path
        ).resolve():
            raise ValueError("PRIVACY_LEDGER_PATH must differ from SQLITE_PATH")
        invite_code = self.auth_invite_code.strip()
        if environment == "production" and (
            len(invite_code) < 20
            or invite_code.lower().startswith(("change-me", "replace-me"))
        ):
            raise ValueError(
                "AUTH_INVITE_CODE must be a non-placeholder value of at least 20 characters"
            )
        encryption_key = self.credential_encryption_key.strip()
        if environment == "production":
            try:
                decoded_key = base64.b64decode(
                    encryption_key,
                    altchars=b"-_",
                    validate=True,
                )
            except (binascii.Error, ValueError):
                decoded_key = b""
            if len(decoded_key) != 32:
                raise ValueError(
                    "CREDENTIAL_ENCRYPTION_KEY must be valid base64 encoding exactly 32 bytes"
                )
            try:
                decoded_backup_key = base64.b64decode(
                    self.backup_signing_key.strip(),
                    altchars=b"-_",
                    validate=True,
                )
            except (binascii.Error, ValueError):
                decoded_backup_key = b""
            if len(decoded_backup_key) != 32:
                raise ValueError(
                    "BACKUP_SIGNING_KEY must be valid base64 encoding exactly 32 bytes"
                )
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            invalid_origin = (
                origin == "*"
                or not parsed.hostname
                or bool(parsed.username or parsed.password)
                or bool(parsed.query or parsed.fragment)
                or parsed.path not in ("", "/")
            )
            insecure_production = environment == "production" and parsed.scheme != "https"
            if invalid_origin or insecure_production:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must contain comma-separated HTTPS origins"
                )
        if environment == "production":
            ledger_id = self.privacy_ledger_id.strip()
            if len(ledger_id) < 16 or ledger_id == "development-ledger":
                raise ValueError(
                    "PRIVACY_LEDGER_ID must be a deployment-unique value of at least 16 characters"
                )
        self.app_env = environment
        return self


settings = Settings()
