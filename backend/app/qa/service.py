from __future__ import annotations

from app.config import settings
from app.llm.client import chat_json, chat_text
from app.rag.citations import apply_citation_guard, retrieved_source_ids
from app.rag.knowledge_lookup import get_by_source_id
from app.rag.retriever import HybridRetriever, format_context

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def ask(question: str, corpus: str = "all", top_k: int = 6) -> dict:
    retriever = get_retriever()
    corp_filter = None if corpus == "all" else corpus
    chunks = retriever.search(question, top_k=top_k, corpus=corp_filter)
    allowed = retrieved_source_ids(chunks)
    context = format_context(chunks)

    if settings.use_demo_llm:
        cites = list(allowed)[:3]
        parts = [f"根据知识库 [{c}]：" for c in cites]
        body = "\n".join(f"- {c.text[:200]}..." for c in chunks[:3]) if chunks else "未命中知识库。"
        return {
            "answer": "（Demo）" + "\n".join(parts) + "\n" + body,
            "citations": [{"source_id": c.source_id, "path": c.path, "excerpt": c.text[:300]} for c in chunks[:5]],
        }

    system = (
        "你是 Agent 技术与云 SA 面试知识助手。仅根据提供的知识片段回答，"
        "并在回答中用 [source_id] 标注引用。输出 JSON：answer, citations（source_id 数组）"
    )
    user = f"知识片段：\n{context}\n\n问题：{question}"
    result = chat_json(system, user)
    result = apply_citation_guard(result, allowed)
    citation_details = []
    for sid in result.get("citations", []):
        doc = get_by_source_id(sid)
        if doc:
            citation_details.append(
                {"source_id": sid, "path": doc["path"], "excerpt": doc["full_text"][:400]}
            )
        else:
            citation_details.append({"source_id": sid, "path": "", "excerpt": ""})
    result["citation_details"] = citation_details
    return result
