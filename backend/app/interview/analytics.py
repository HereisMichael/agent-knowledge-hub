"""Quiz attempt analytics and level tables."""

from __future__ import annotations

from collections import defaultdict

from app.db import store
from app.interview.questions import get_question, load_questions


def build_quiz_analytics(user_id: str = "default") -> dict:
    history = store.list_quiz_history(user_id, limit=500)
    by_q: dict[str, list[dict]] = defaultdict(list)
    for row in history:
        score = row.get("ai_score")
        if score is None:
            score = row.get("self_score")
        by_q[row["question_id"]].append(
            {
                "id": row["id"],
                "score": score,
                "created_at": row["created_at"],
                "answer_preview": (row.get("answer_text") or "")[:120],
            }
        )

    question_rows = []
    cat_scores: dict[str, list[int]] = defaultdict(list)
    vendor_scores: dict[str, list[int]] = defaultdict(list)

    for qid, attempts in by_q.items():
        q = get_question(qid) or {}
        scores = [a["score"] for a in attempts if a["score"] is not None]
        if not scores:
            continue
        first, last, best = scores[0], scores[-1], max(scores)
        delta = last - scores[-2] if len(scores) > 1 else None
        if delta is None:
            trend = "new"
        elif delta > 3:
            trend = "up"
        elif delta < -3:
            trend = "down"
        else:
            trend = "stable"

        cat = q.get("category", "other")
        vendor = q.get("vendor", "")
        cat_scores[cat].extend(scores)
        if vendor:
            vendor_scores[vendor].extend(scores)

        ref = store.get_reference_answer(user_id, qid)
        question_rows.append(
            {
                "question_id": qid,
                "question": q.get("question", qid)[:80],
                "category": cat,
                "vendor": vendor,
                "attempts": len(attempts),
                "first_score": first,
                "last_score": last,
                "best_score": best,
                "avg_score": round(sum(scores) / len(scores), 1),
                "trend": trend,
                "score_series": scores,
                "has_reference": bool(ref and ref.get("reference_text")),
                "reference_updated_at": ref.get("updated_at") if ref else None,
            }
        )

    question_rows.sort(key=lambda x: x["last_score"])

    def _avg(lst: list[int]) -> float:
        return round(sum(lst) / len(lst), 1) if lst else 0.0

    summary = {
        "total_attempts": len(history),
        "questions_practiced": len(question_rows),
        "overall_avg": _avg([s for row in question_rows for s in row["score_series"]]),
        "by_category": {k: _avg(v) for k, v in cat_scores.items()},
        "by_vendor": {k: _avg(v) for k, v in vendor_scores.items()},
    }

    return {
        "summary": summary,
        "questions": question_rows,
        "recent": history[:20],
    }
