from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_base_url: str = "https://api.cursor.com/v1"
    llm_api_key: str = ""
    llm_model: str = "composer-2.5"
    demo_mode: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    chroma_path: str = "./data/chroma"
    sqlite_path: str = "./data/hub.db"
    knowledge_path: str = "../knowledge"
    ingest_extra_dirs: str = ""

    admin_api_key: str = "change-me-admin-key"
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


settings = Settings()
