import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.migrate_legacy_assets import sha256_file, verify_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "corpus/migration-manifest.json"
pytestmark = pytest.mark.skipif(
    not MANIFEST_PATH.is_file(),
    reason="Private migration corpus is intentionally absent from public clones",
)
EXPECTED_COUNTS = {
    "agent-interviews": 37,
    "agent-review": 13,
    "maas-interviews": 21,
}


def test_private_corpus_manifest_has_expected_inventory() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["corpus_counts"] == EXPECTED_COUNTS
    assert len(manifest["entries"]) == 71
    counts = Counter(entry["corpus"] for entry in manifest["entries"])
    assert dict(counts) == EXPECTED_COUNTS
    assert all(entry["status"] == "copied" for entry in manifest["entries"])


def test_every_manifest_hash_matches_the_target_file() -> None:
    assert verify_manifest(ROOT, MANIFEST_PATH) == {"verified": 71}


def test_private_assets_are_not_inside_public_knowledge_roots() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest["entries"]:
        target = Path(entry["target_relative"])
        assert target.parts[:2] == ("corpus", "private")
        assert "knowledge" not in target.parts
        assert sha256_file(ROOT / target) == entry["sha256"]
