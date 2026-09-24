import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts import migrate_legacy_assets as migration
from scripts.migrate_legacy_assets import CORPORA, migrate_assets, verify_manifest


def _write_files(root: Path, directory: str, markdown: int, other: int) -> None:
    source = root / directory
    source.mkdir(parents=True)
    for index in range(markdown):
        (source / f"doc-{index:02d}.md").write_text(
            f"# document {index}\n\n\u6765\u6e90\uff1ahttps://example.com/{index}\n",
            encoding="utf-8",
        )
    for index in range(other):
        (source / f"attachment-{index:02d}.bin").write_bytes(bytes([index, 1, 2, 3]))


def _fixture_source(root: Path) -> None:
    _write_files(root, "20260629-agent\u9762", markdown=37, other=0)
    _write_files(root, "agent\u9762-\u590d\u76d8", markdown=12, other=1)
    _write_files(root, "2026-07-01-maas\u89e3\u51b3\u65b9\u6848_\u9762", markdown=20, other=1)


def test_corpus_specs_use_exact_runtime_source_names() -> None:
    assert tuple(spec.source_name for spec in CORPORA) == (
        "20260629-agent\u9762",
        "agent\u9762-\u590d\u76d8",
        "2026-07-01-maas\u89e3\u51b3\u65b9\u6848_\u9762",
    )


def test_migrate_assets_copies_all_files_and_writes_manifest(tmp_path: Path) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)

    manifest = migrate_assets(source_root, target_root)

    assert manifest["schema_version"] == 1
    assert len(manifest["entries"]) == 71
    counts = manifest["corpus_counts"]
    assert counts == {
        "agent-interviews": 37,
        "agent-review": 13,
        "maas-interviews": 21,
    }
    entry = manifest["entries"][0]
    copied = target_root / entry["target_relative"]
    assert copied.is_file()
    assert hashlib.sha256(copied.read_bytes()).hexdigest() == entry["sha256"]
    assert entry["status"] == "copied"


def test_identical_rerun_is_idempotent(tmp_path: Path) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)

    first = migrate_assets(source_root, target_root)
    manifest_path = target_root / "corpus/migration-manifest.json"
    first_manifest_bytes = manifest_path.read_bytes()
    first_manifest_mtime = manifest_path.stat().st_mtime_ns
    second = migrate_assets(source_root, target_root)
    second_manifest_bytes = manifest_path.read_bytes()
    second_manifest_mtime = manifest_path.stat().st_mtime_ns

    comparable = lambda manifest: [
        (entry["target_relative"], entry["size"], entry["sha256"])
        for entry in manifest["entries"]
    ]
    assert comparable(first) == comparable(second)
    assert first_manifest_bytes == second_manifest_bytes
    assert first_manifest_mtime == second_manifest_mtime


def test_source_change_fails_closed_without_altering_destination_or_manifest(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)

    manifest = migrate_assets(source_root, target_root)
    manifest_path = target_root / "corpus/migration-manifest.json"
    first_manifest_bytes = manifest_path.read_bytes()
    destination = target_root / manifest["entries"][0]["target_relative"]
    first_destination_bytes = destination.read_bytes()
    changed_source = source_root / "20260629-agent\u9762" / "doc-00.md"
    changed_source.write_bytes(b"# changed\n")

    with pytest.raises(ValueError, match="destination collision"):
        migrate_assets(source_root, target_root)

    assert destination.read_bytes() == first_destination_bytes
    assert manifest_path.read_bytes() == first_manifest_bytes


def test_different_destination_bytes_fail_closed(tmp_path: Path) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)
    manifest = migrate_assets(source_root, target_root)
    destination = target_root / manifest["entries"][0]["target_relative"]
    destination.write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="destination collision"):
        migrate_assets(source_root, target_root)


def test_verify_manifest_detects_tampering(tmp_path: Path) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)
    migrate_assets(source_root, target_root)
    manifest_path = target_root / "corpus/migration-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    destination = target_root / manifest["entries"][0]["target_relative"]
    destination.write_bytes(b"changed")

    with pytest.raises(ValueError, match="hash mismatch"):
        verify_manifest(target_root, manifest_path)


def _target_snapshot(target_root: Path) -> dict[str, bytes]:
    if not target_root.exists():
        return {}
    return {
        path.relative_to(target_root).as_posix(): path.read_bytes()
        for path in target_root.rglob("*")
        if path.is_file()
    }


def test_late_source_deletion_leaves_existing_migration_unchanged(tmp_path: Path) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)
    migrate_assets(source_root, target_root)
    before = _target_snapshot(target_root)
    (source_root / CORPORA[-1].source_name / "doc-19.md").unlink()

    with pytest.raises(ValueError, match="unexpected source inventory"):
        migrate_assets(source_root, target_root)

    assert _target_snapshot(target_root) == before


def test_same_count_source_rename_is_rejected_without_changes(tmp_path: Path) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)
    migrate_assets(source_root, target_root)
    before = _target_snapshot(target_root)
    original = source_root / CORPORA[-1].source_name / "doc-19.md"
    original.rename(original.with_name("renamed.md"))

    with pytest.raises(ValueError, match="source inventory"):
        migrate_assets(source_root, target_root)

    assert _target_snapshot(target_root) == before


def test_late_destination_collision_does_not_copy_earlier_files(tmp_path: Path) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)
    collision = (
        target_root
        / "corpus"
        / "private"
        / CORPORA[-1].target_name
        / "doc-19.md"
    )
    collision.parent.mkdir(parents=True)
    collision.write_bytes(b"collision")
    before = _target_snapshot(target_root)

    with pytest.raises(ValueError, match="destination collision"):
        migrate_assets(source_root, target_root)

    assert _target_snapshot(target_root) == before
    assert not (target_root / "corpus" / "migration-manifest.json").exists()


def test_late_copy_failure_cleans_staging_and_leaves_target_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    target_root.mkdir()
    _fixture_source(source_root)
    real_copy2 = shutil.copy2
    calls = 0

    def fail_late(source: Path, destination: Path):
        nonlocal calls
        calls += 1
        if calls == 70:
            raise OSError("simulated copy failure")
        return real_copy2(source, destination)

    monkeypatch.setattr(migration.shutil, "copy2", fail_late)

    with pytest.raises(OSError, match="simulated copy failure"):
        migrate_assets(source_root, target_root)

    assert _target_snapshot(target_root) == {}
    assert list(target_root.glob(".migration-*")) == []


def _migrate_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    source_root = tmp_path / "legacy"
    target_root = tmp_path / "target"
    _fixture_source(source_root)
    migrate_assets(source_root, target_root)
    manifest_path = target_root / "corpus" / "migration-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return target_root, manifest_path, manifest


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda manifest: manifest.update(schema_version=2), "schema_version"),
        (
            lambda manifest: manifest.update(
                corpus_counts={"agent-interviews": 71, "agent-review": 0, "maas-interviews": 0}
            ),
            "corpus_counts",
        ),
        (lambda manifest: manifest["entries"][0].update(status="pending"), "status"),
        (lambda manifest: manifest.update(entries=[]), "entries"),
        (
            lambda manifest: manifest["entries"].__setitem__(1, dict(manifest["entries"][0])),
            "duplicate",
        ),
    ],
)
def test_verify_manifest_rejects_malformed_inventory(
    tmp_path: Path,
    mutation,
    message: str,
) -> None:
    target_root, manifest_path, manifest = _migrate_fixture(tmp_path)
    mutation(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        verify_manifest(target_root, manifest_path)


def test_verify_manifest_rejects_non_object_top_level(tmp_path: Path) -> None:
    target_root, manifest_path, _ = _migrate_fixture(tmp_path)
    manifest_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest must be an object"):
        verify_manifest(target_root, manifest_path)


def test_verify_manifest_rejects_target_traversal_even_when_hash_matches(
    tmp_path: Path,
) -> None:
    target_root, manifest_path, manifest = _migrate_fixture(tmp_path)
    first = manifest["entries"][0]
    original = target_root / first["target_relative"]
    outside = target_root.parent / "outside.md"
    outside.write_bytes(original.read_bytes())
    first["target_relative"] = "../outside.md"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="traversal|outside private corpus"):
        verify_manifest(target_root, manifest_path)


def test_verify_manifest_rejects_extra_private_file(tmp_path: Path) -> None:
    target_root, manifest_path, manifest = _migrate_fixture(tmp_path)
    extra = target_root / "corpus" / "private" / manifest["entries"][0]["corpus"] / "extra.md"
    extra.write_text("extra", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected private file"):
        verify_manifest(target_root, manifest_path)


@pytest.mark.parametrize(
    "relative_extra",
    [Path("root-extra.md"), Path("other") / "extra.md"],
    ids=["private-root", "unexpected-corpus"],
)
def test_verify_manifest_rejects_extra_file_anywhere_beneath_private_root(
    tmp_path: Path,
    relative_extra: Path,
) -> None:
    target_root, manifest_path, _ = _migrate_fixture(tmp_path)
    extra = target_root / "corpus" / "private" / relative_extra
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text("extra", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected private file"):
        verify_manifest(target_root, manifest_path)
