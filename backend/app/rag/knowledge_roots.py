from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from app.config import settings


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def resolve_knowledge_roots(roots: Iterable[Path] | None = None) -> list[Path]:
    """Resolve public knowledge roots and reject any private-corpus overlap."""
    configured = (
        list(roots)
        if roots is not None
        else [settings.knowledge_dir, *settings.extra_knowledge_dirs]
    )
    private_root = (Path(settings.project_root).resolve() / "corpus" / "private").resolve()
    resolved: list[Path] = []
    for configured_root in configured:
        root = Path(configured_root).resolve()
        if _overlaps(root, private_root):
            raise ValueError(f"knowledge root overlaps private corpus: {root}")
        if root not in resolved:
            resolved.append(root)
    return resolved
