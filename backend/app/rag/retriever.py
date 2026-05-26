from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from rank_bm25 import BM25Okapi

from app.config import settings
from app.rag.ingest import COLLECTION_NAME, chunk_text, parse_front_matter


@dataclass
class RetrievedChunk:
    source_id: str
    text: str
    score: float
    path: str
    corpus: str = "tech"


class HybridRetriever:
    def __init__(self) -> None:
        self._chroma = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._chroma.get_or_create_collection(COLLECTION_NAME)
        self._bm25_docs: list[str] = []
        self._bm25_meta: list[dict] = []
        self._bm25: BM25Okapi | None = None
        self.reload_bm25()

    def reload_bm25(self) -> None:
        self._bm25_docs = []
        self._bm25_meta = []
        self._bm25 = None
        roots = [settings.knowledge_dir, *settings.extra_knowledge_dirs]
        for root in roots:
            if not root.exists():
                continue
            for md_path in root.rglob("*.md"):
                text = md_path.read_text(encoding="utf-8")
                meta, body = parse_front_matter(text)
                source_id = meta.get("source_id", md_path.stem)
                corpus = str(meta.get("corpus", meta.get("topic", "tech")))
                for chunk in chunk_text(body):
                    self._bm25_docs.append(chunk)
                    self._bm25_meta.append(
                        {
                            "source_id": source_id,
                            "path": str(md_path.relative_to(root)),
                            "corpus": corpus,
                        }
                    )
        if self._bm25_docs:
            self._bm25 = BM25Okapi([d.split() for d in self._bm25_docs])

    def search(
        self, query: str, top_k: int = 6, corpus: str | None = None
    ) -> list[RetrievedChunk]:
        where = {"corpus": corpus} if corpus and corpus != "all" else None
        vector_hits: list[RetrievedChunk] = []
        try:
            kwargs: dict = {"query_texts": [query], "n_results": top_k}
            if where:
                kwargs["where"] = where
            res = self._collection.query(**kwargs)
            for i, doc in enumerate(res["documents"][0]):
                meta = res["metadatas"][0][i]
                dist = res["distances"][0][i] if res.get("distances") else 0.0
                vector_hits.append(
                    RetrievedChunk(
                        source_id=meta.get("source_id", "unknown"),
                        text=doc,
                        score=1.0 - dist,
                        path=meta.get("path", ""),
                        corpus=meta.get("corpus", "tech"),
                    )
                )
        except Exception:
            pass

        bm25_hits: list[RetrievedChunk] = []
        if self._bm25 and self._bm25_docs:
            scores = self._bm25.get_scores(query.split())
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: top_k * 2]
            for i in ranked:
                if scores[i] <= 0:
                    continue
                meta = self._bm25_meta[i]
                if corpus and corpus != "all" and meta.get("corpus") != corpus:
                    continue
                bm25_hits.append(
                    RetrievedChunk(
                        source_id=meta["source_id"],
                        text=self._bm25_docs[i],
                        score=float(scores[i]),
                        path=meta["path"],
                        corpus=meta.get("corpus", "tech"),
                    )
                )

        merged: dict[str, RetrievedChunk] = {}
        for hit in vector_hits + bm25_hits:
            key = f"{hit.source_id}:{hit.text[:80]}"
            if key not in merged or hit.score > merged[key].score:
                merged[key] = hit
        return sorted(merged.values(), key=lambda x: x.score, reverse=True)[:top_k]


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "（未检索到相关知识，请基于通用最佳实践回答，并标注需人工补充证据。）"
    lines = [f"[{c.source_id}] {c.text[:500]}" for c in chunks]
    return "\n\n".join(lines)
