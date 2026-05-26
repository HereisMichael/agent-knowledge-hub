from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.db import store


def load_manifest() -> list[dict]:
    path = Path(settings.project_root).resolve() / "labs" / "manifest.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def recommend_labs(
    weakness_tags: list[str] | None = None,
    gaps: list[str] | None = None,
    user_id: str = "default",
    limit: int = 3,
) -> list[dict]:
    manifest = load_manifest()
    completed = set(store.list_completed_labs(user_id))
    tags = set(weakness_tags or [])
    gap_text = " ".join(gaps or []).lower()

    tag_map = {
        "架构": "architecture",
        "rag": "rag",
        "agent": "agent",
        "合规": "compliance",
        "产品": "product",
        "竞品": "product",
        "openclaw": "agent",
        "harness": "agent",
    }
    for g in gaps or []:
        for k, v in tag_map.items():
            if k in g.lower():
                tags.add(v)

    scored: list[tuple[int, dict]] = []
    for lab in manifest:
        if lab["id"] in completed:
            continue
        lab_tags = set(lab.get("weakness_tags", []))
        score = len(tags & lab_tags) * 10
        if gap_text:
            for t in lab_tags:
                if t in gap_text:
                    score += 5
        scored.append((score, lab))

    scored.sort(key=lambda x: (-x[0], x[1].get("effort_hours", 99)))
    return [lab for _, lab in scored[:limit]] or manifest[:limit]
