"""Ingest markdown knowledge into Chroma + BM25 corpus."""

from __future__ import annotations

import json
import re
from pathlib import Path

import chromadb
import yaml
from chromadb.config import Settings as ChromaSettings

from app.config import settings

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
COLLECTION_NAME = "agent_kb"


def parse_front_matter(text: str) -> tuple[dict, str]:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    body = text[m.end() :]
    return meta, body


def chunk_text(body: str, chunk_size: int = 600) -> list[str]:
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        if len(buf) + len(p) < chunk_size:
            buf = f"{buf}\n\n{p}".strip() if buf else p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks or [body[:chunk_size]]


def _knowledge_roots() -> list[Path]:
    roots = [settings.knowledge_dir]
    roots.extend(settings.extra_knowledge_dirs)
    return roots


def _manifest_path() -> Path:
    p = Path(settings.chroma_path).parent / "ingest_manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_manifest() -> dict:
    p = _manifest_path()
    if not p.exists():
        return {"files": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"files": {}}


def _save_manifest(data: dict) -> None:
    _manifest_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _file_signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _index_file(
    collection,
    md_path: Path,
    root: Path,
) -> tuple[list[str], str]:
    text = md_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    source_id = meta.get("source_id", md_path.stem)
    corpus = str(meta.get("corpus", meta.get("topic", "tech")))
    rel_path = str(md_path.relative_to(root))
    chunk_ids: list[str] = []
    for i, chunk in enumerate(chunk_text(body)):
        doc_id = f"{source_id}__{i}"
        collection.upsert(
            ids=[doc_id],
            documents=[chunk],
            metadatas=[
                {
                    "source_id": source_id,
                    "corpus": corpus,
                    "type": str(meta.get("type", "unknown")),
                    "topic": str(meta.get("topic", "")),
                    "path": rel_path,
                    "root": str(root.resolve()),
                }
            ],
        )
        chunk_ids.append(doc_id)
    return chunk_ids, source_id


def ingest_knowledge(knowledge_dirs: list[Path] | None = None, *, full: bool = False) -> dict:
    """Ingest markdown into Chroma. Incremental by default (mtime manifest)."""
    if full:
        return _ingest_full(knowledge_dirs)
    return ingest_knowledge_incremental(knowledge_dirs)


def _ingest_full(knowledge_dirs: list[Path] | None = None) -> dict:
    roots = knowledge_dirs or _knowledge_roots()
    client = chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    manifest: dict = {"files": {}}
    count = 0
    for root in roots:
        if not root.exists():
            continue
        for md_path in root.rglob("*.md"):
            if md_path.name.startswith("."):
                continue
            chunk_ids, source_id = _index_file(collection, md_path, root)
            key = str(md_path.resolve())
            manifest["files"][key] = {
                "signature": _file_signature(md_path),
                "source_id": source_id,
                "chunk_ids": chunk_ids,
                "root": str(root.resolve()),
            }
            count += len(chunk_ids)

    _save_manifest(manifest)
    return {
        "mode": "full",
        "chunks_indexed": count,
        "files_processed": len(manifest["files"]),
        "files_skipped": 0,
        "files_removed": 0,
    }


def ingest_knowledge_incremental(knowledge_dirs: list[Path] | None = None) -> dict:
    roots = knowledge_dirs or _knowledge_roots()
    client = chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    manifest = _load_manifest()
    files: dict = manifest.setdefault("files", {})
    seen_keys: set[str] = set()
    count = 0
    skipped = 0

    for root in roots:
        if not root.exists():
            continue
        for md_path in root.rglob("*.md"):
            if md_path.name.startswith("."):
                continue
            key = str(md_path.resolve())
            seen_keys.add(key)
            sig = _file_signature(md_path)
            entry = files.get(key)
            if entry and entry.get("signature") == sig:
                skipped += 1
                count += len(entry.get("chunk_ids", []))
                continue

            if entry and entry.get("chunk_ids"):
                try:
                    collection.delete(ids=entry["chunk_ids"])
                except Exception:
                    pass

            chunk_ids, source_id = _index_file(collection, md_path, root)
            files[key] = {
                "signature": sig,
                "source_id": source_id,
                "chunk_ids": chunk_ids,
                "root": str(root.resolve()),
            }
            count += len(chunk_ids)

    removed = 0
    for key in list(files.keys()):
        if key not in seen_keys:
            entry = files.pop(key)
            ids = entry.get("chunk_ids", [])
            if ids:
                try:
                    collection.delete(ids=ids)
                except Exception:
                    pass
            removed += 1

    _save_manifest(manifest)
    return {
        "mode": "incremental",
        "chunks_indexed": count,
        "files_processed": len(seen_keys) - skipped,
        "files_skipped": skipped,
        "files_removed": removed,
    }
