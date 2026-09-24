import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/tests/test_smoke.py",
    "backend/requirements.txt",
    "backend/.env.example",
    "backend/Dockerfile",
    "web/src/App.tsx",
    "web/src/api.ts",
    "web/src/pages/Dashboard.tsx",
    "web/src/components/shell/AppShell.tsx",
    "web/src/styles/tokens.css",
    "web/package.json",
    "web/package-lock.json",
    "web/tsconfig.json",
    "web/vite.config.ts",
    "web/vitest.config.ts",
    "web/nginx.conf",
    "web/Dockerfile",
    "knowledge/interview/questions.jsonl",
    "content/feeds.yaml",
    "labs/manifest.json",
    "eval/run_eval.py",
    "docker-compose.yml",
    "README.md",
    "PRODUCT.md",
    "DESIGN.md",
    "LICENSE",
}

FORBIDDEN_PARTS = {
    ".env",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
}

FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc"}

FORBIDDEN_FILES = {"eval/eval-report.json"}


def test_required_baseline_files_exist() -> None:
    missing = sorted(path for path in REQUIRED_FILES if not (ROOT / path).is_file())
    assert missing == []


def test_runtime_and_secret_artifacts_are_not_migrated() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    offenders: list[str] = []
    for line in result.stdout.splitlines():
        relative = Path(line)
        if relative.as_posix() in FORBIDDEN_FILES:
            offenders.append(relative.as_posix())
        elif any(part in FORBIDDEN_PARTS for part in relative.parts):
            offenders.append(relative.as_posix())
        elif relative.suffix.lower() in FORBIDDEN_SUFFIXES:
            offenders.append(relative.as_posix())
    assert offenders == []


def test_development_dependency_file_enables_pytest() -> None:
    requirements = (ROOT / "backend/requirements-dev.txt").read_text(encoding="utf-8")
    lines = {
        line.strip()
        for line in requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "-r requirements.txt" in lines
    assert any(line.startswith("pytest>=") for line in lines)


def test_readme_typecheck_uses_the_web_project_config() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert (
        "& '.\\web\\node_modules\\.bin\\tsc.cmd' --project "
        "'.\\web\\tsconfig.json' --noEmit --incremental false"
    ) in readme


def test_readme_documents_the_training_console_and_frontend_tests() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "今日训练" in readme
    assert "npm.cmd run test:run" in readme


def test_documented_development_api_matches_resolved_vite_proxy() -> None:
    script = """
import { loadConfigFromFile } from './web/node_modules/vite/dist/node/index.js';
const loaded = await loadConfigFromFile(
  {command: 'serve', mode: 'development'},
  './web/vite.config.ts',
  process.cwd(),
);
console.log(JSON.stringify(loaded.config.server));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    server = json.loads(result.stdout)
    proxy_target = server["proxy"]["/api"]["target"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    documented_urls = set(re.findall(r"https?://[^\s*)]+", readme))

    assert proxy_target == "http://127.0.0.1:8001"
    assert f"{proxy_target}/docs" in documented_urls


def test_all_local_readme_links_resolve_to_files() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
    targets.extend(re.findall(r'href="([^"]+)"', readme))
    local_targets = [target for target in targets if not target.startswith(("#", "http://", "https://"))]

    missing = [target for target in local_targets if not (ROOT / target).is_file()]
    assert missing == []
