from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["KNOWLEDGE_PATH"] = str(ROOT / "knowledge")
os.environ["SQLITE_PATH"] = str(ROOT / "backend" / "data" / "test_hub.db")
os.environ["CHROMA_PATH"] = str(ROOT / "backend" / "data" / "chroma_test")
os.environ["PROJECT_ROOT"] = str(ROOT)
os.environ["CONTENT_ROOT"] = str(ROOT / "content")
os.environ["DEMO_MODE"] = "true"
os.environ["CONTENT_SCHEDULER_ENABLED"] = "false"

from app.config import settings  # noqa: E402
from app.rag import ingest, knowledge_lookup, retriever as retriever_module  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402


def _configure_roots(monkeypatch: pytest.MonkeyPatch, project_root: Path, root: Path) -> None:
    monkeypatch.setattr(settings, "project_root", str(project_root))
    monkeypatch.setattr(settings, "knowledge_path", str(root))
    monkeypatch.setattr(settings, "ingest_extra_dirs", "")


@pytest.mark.parametrize("relative_root", ["corpus/private", "corpus/private/nested", "."])
def test_source_lookup_rejects_every_private_root_overlap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_root: str,
) -> None:
    project_root = tmp_path / "project"
    private_root = project_root / "corpus" / "private"
    private_root.mkdir(parents=True)
    selected_root = (project_root / relative_root).resolve()
    selected_root.mkdir(parents=True, exist_ok=True)
    _configure_roots(monkeypatch, project_root, selected_root)

    with pytest.raises(ValueError, match="private corpus"):
        knowledge_lookup.get_by_source_id("anything")


def test_full_ingest_rejects_private_root_before_creating_an_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    private_root = project_root / "corpus" / "private"
    private_root.mkdir(parents=True)
    _configure_roots(monkeypatch, project_root, private_root)
    client_created = False

    def unexpected_client(*args, **kwargs):
        nonlocal client_created
        client_created = True
        raise AssertionError("index client created before root validation")

    monkeypatch.setattr(ingest.chromadb, "PersistentClient", unexpected_client)

    with pytest.raises(ValueError, match="private corpus"):
        ingest.ingest_knowledge(full=True)

    assert client_created is False


def test_bm25_reload_rejects_private_root_before_mutating_existing_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    private_root = project_root / "corpus" / "private"
    private_root.mkdir(parents=True)
    _configure_roots(monkeypatch, project_root, private_root)
    retriever = object.__new__(HybridRetriever)
    retriever._bm25_docs = ["existing"]
    retriever._bm25_meta = [{"source_id": "existing"}]
    retriever._bm25 = object()

    with pytest.raises(ValueError, match="private corpus"):
        retriever.reload_bm25()

    assert retriever._bm25_docs == ["existing"]
    assert retriever._bm25_meta == [{"source_id": "existing"}]
    assert retriever._bm25 is not None


def test_hybrid_retriever_rejects_private_root_before_creating_vector_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    private_root = project_root / "corpus" / "private"
    private_root.mkdir(parents=True)
    _configure_roots(monkeypatch, project_root, private_root)
    client_created = False

    def unexpected_client(*args, **kwargs):
        nonlocal client_created
        client_created = True
        raise AssertionError("vector index client created before root validation")

    monkeypatch.setattr(retriever_module.chromadb, "PersistentClient", unexpected_client)

    with pytest.raises(ValueError, match="private corpus"):
        HybridRetriever()

    assert client_created is False
