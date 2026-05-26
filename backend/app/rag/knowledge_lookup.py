from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.rag.ingest import chunk_text, parse_front_matter


def _all_roots() -> list[Path]:
    return [settings.knowledge_dir, *settings.extra_knowledge_dirs]


def get_by_source_id(source_id: str) -> dict | None:
    for root in _all_roots():
        if not root.exists():
            continue
        for md_path in root.rglob("*.md"):
            text = md_path.read_text(encoding="utf-8")
            meta, body = parse_front_matter(text)
            if meta.get("source_id") != source_id:
                continue
            chunks = chunk_text(body)
            return {
                "source_id": source_id,
                "corpus": meta.get("corpus", meta.get("topic", "tech")),
                "type": meta.get("type", "unknown"),
                "path": str(md_path.relative_to(root)),
                "title": md_path.stem,
                "chunks": chunks,
                "full_text": body.strip(),
            }
    return None


def list_source_ids(corpus: str | None = None) -> list[str]:
    ids: list[str] = []
    for root in _all_roots():
        if not root.exists():
            continue
        for md_path in root.rglob("*.md"):
            meta, _ = parse_front_matter(md_path.read_text(encoding="utf-8"))
            if corpus and meta.get("corpus") != corpus and meta.get("topic") != corpus:
                continue
            sid = meta.get("source_id")
            if sid:
                ids.append(sid)
    return sorted(set(ids))
