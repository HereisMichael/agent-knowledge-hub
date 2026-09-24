from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_compose_waits_for_healthy_api_and_persists_runtime_data():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "/api/health/ready" in compose
    assert "/healthz" in compose
    assert "condition: service_healthy" in compose
    assert "./backend/data:/app/data" in compose
    assert "./privacy-ledger:/app/privacy-ledger" in compose
    assert "volume-init:" in compose
    assert "service_completed_successfully" in compose
    assert "chown -R app:app /app/data /app/privacy-ledger" in compose
    assert "PRIVACY_LEDGER_PATH: /app/privacy-ledger/account-deletions.db" in compose
    assert "restart: unless-stopped" in compose
    assert "scheduler:" in compose
    assert "python -m app.scheduler.worker" in compose
    assert 'CONTENT_SCHEDULER_ENABLED: "false"' in compose


def test_nginx_exposes_health_and_security_headers():
    nginx = (ROOT / "web" / "nginx.conf").read_text(encoding="utf-8")

    assert "location = /healthz" in nginx
    assert "X-Content-Type-Options" in nginx
    assert "X-Frame-Options" in nginx
    assert "Referrer-Policy" in nginx
    assert "proxy_set_header X-Forwarded-Proto" in nginx


def test_container_access_logs_cannot_capture_queries_or_dynamic_paths():
    nginx = (ROOT / "web" / "nginx.conf").read_text(encoding="utf-8")
    api_dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "access_log off;" in nginx
    assert "$request" not in nginx
    assert "$request_uri" not in nginx
    assert "$args" not in nginx
    assert "--no-access-log" in api_dockerfile


def test_ci_runs_backend_assets_frontend_tests_and_build():
    workflow = ROOT / ".github" / "workflows" / "ci.yml"
    content = workflow.read_text(encoding="utf-8")

    assert "working-directory: backend" in content
    assert "python -m pytest tests -q" in content
    assert "npm run test:run" in content
    assert "npm run build" in content
    assert "docker compose config --quiet" in content
    assert "docker compose build" in content
    assert "python -m app.privacy.ledger_cli init" in content
    assert "python -m app.privacy.ledger_cli verify" in content
    assert "docker compose run --rm --no-deps volume-init" in content
    assert "curl --fail http://127.0.0.1:8001/api/health/ready" in content


def test_docker_contexts_exclude_runtime_and_dependency_directories():
    backend_ignore = (ROOT / "backend" / ".dockerignore").read_text(encoding="utf-8")
    web_ignore = (ROOT / "web" / ".dockerignore").read_text(encoding="utf-8")

    assert "data" in backend_ignore
    assert ".env" in backend_ignore
    assert "node_modules" in web_ignore
    assert "dist" in web_ignore


def test_production_documents_explicit_privacy_ledger_bootstrap():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    environment = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")

    assert "PRIVACY_LEDGER_ID=" in environment
    assert "python -m app.privacy.ledger_cli init" in readme
    assert "python -m app.privacy.ledger_cli verify" in readme
    assert "不能与主数据库一起恢复" in readme
