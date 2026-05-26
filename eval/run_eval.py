#!/usr/bin/env python3
"""Retrieval recall@k eval without LLM."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.rag.ingest import ingest_knowledge  # noqa: E402
from app.rag.retriever import HybridRetriever  # noqa: E402


def run_file(path: Path, corpus: str | None, k: int = 6) -> dict:
    retriever = HybridRetriever()
    hits = 0
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        total += 1
        results = retriever.search(row["query"], top_k=k, corpus=corpus)
        found = {r.source_id for r in results}
        expected = set(row.get("expected_source_ids", []))
        if expected & found:
            hits += 1
    return {"file": path.name, "recall_at_k": hits / total if total else 0, "hits": hits, "total": total}


def main() -> None:
    settings.knowledge_path = str(ROOT / "knowledge")
    settings.chroma_path = str(ROOT / "backend" / "data" / "chroma_eval")
    ingest_knowledge()
    reports = [
        run_file(ROOT / "eval" / "golden_tech.jsonl", None),
        run_file(ROOT / "eval" / "golden_interview.jsonl", "interview"),
    ]
    out = ROOT / "eval" / "eval-report.json"
    out.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
