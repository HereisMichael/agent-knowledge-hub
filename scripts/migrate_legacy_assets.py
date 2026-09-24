from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class CorpusSpec:
    source_name: str
    target_name: str
    expected_files: int
    expected_markdown: int


CORPORA = (
    CorpusSpec("20260629-agent\u9762", "agent-interviews", 37, 37),
    CorpusSpec("agent\u9762-\u590d\u76d8", "agent-review", 13, 12),
    CorpusSpec("2026-07-01-maas\u89e3\u51b3\u65b9\u6848_\u9762", "maas-interviews", 21, 20),
)
EXPECTED_COUNTS = {spec.target_name: spec.expected_files for spec in CORPORA}
SPEC_BY_TARGET = {spec.target_name: spec for spec in CORPORA}
ENTRY_FIELDS = {
    "corpus",
    "source_absolute",
    "source_relative",
    "target_relative",
    "size",
    "sha256",
    "status",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_files(source: Path, spec: CorpusSpec) -> list[Path]:
    files = sorted(path for path in source.rglob("*") if path.is_file())
    markdown = sum(path.suffix.lower() == ".md" for path in files)
    if len(files) != spec.expected_files or markdown != spec.expected_markdown:
        raise ValueError(
            f"unexpected source inventory for {spec.source_name}: "
            f"files={len(files)} markdown={markdown}"
        )
    return files


def _build_inventory(source_root: Path) -> tuple[list[dict[str, object]], dict[str, int]]:
    entries: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for spec in CORPORA:
        source = source_root / spec.source_name
        if not source.is_dir():
            raise ValueError(f"missing source corpus: {source}")
        files = _source_files(source, spec)
        counts[spec.target_name] = len(files)
        for path in files:
            relative = path.relative_to(source)
            entries.append(
                {
                    "corpus": spec.target_name,
                    "source_absolute": str(path.resolve()),
                    "source_relative": (Path(spec.source_name) / relative).as_posix(),
                    "target_relative": (
                        Path("corpus") / "private" / spec.target_name / relative
                    ).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "status": "copied",
                }
            )
    entries.sort(key=lambda item: str(item["target_relative"]))
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"unexpected corpus counts: {counts}")
    if len({str(entry["target_relative"]).casefold() for entry in entries}) != len(entries):
        raise ValueError("duplicate destination in source inventory")
    return entries, counts


def _read_manifest(manifest_path: Path) -> dict[str, object]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid migration manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    return manifest


def _relative_path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} contains traversal or is absolute: {value}")
    return path


def _validate_manifest_shape(manifest: dict[str, object]) -> list[dict[str, object]]:
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    if not isinstance(manifest.get("generated_at"), str) or not manifest["generated_at"].strip():
        raise ValueError("generated_at must be a non-empty string")
    if not isinstance(manifest.get("source_root"), str) or not manifest["source_root"].strip():
        raise ValueError("source_root must be a non-empty string")
    if manifest.get("corpus_counts") != EXPECTED_COUNTS:
        raise ValueError(f"corpus_counts must equal {EXPECTED_COUNTS}")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != sum(EXPECTED_COUNTS.values()):
        raise ValueError("entries must contain exactly 71 items")
    if not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("every manifest entry must be an object")
    return entries


def verify_manifest(target_root: Path, manifest_path: Path) -> dict[str, int]:
    target_root = target_root.resolve()
    manifest = _read_manifest(manifest_path)
    entries = _validate_manifest_shape(manifest)
    source_absolute_seen: set[str] = set()
    source_relative_seen: set[str] = set()
    target_seen: set[str] = set()
    expected_targets: set[Path] = set()
    expected_target_relatives: set[str] = set()
    entry_counts: Counter[str] = Counter()

    for index, entry in enumerate(entries, 1):
        if set(entry) != ENTRY_FIELDS:
            raise ValueError(f"entry {index} fields are malformed")
        corpus = entry["corpus"]
        if not isinstance(corpus, str) or corpus not in SPEC_BY_TARGET:
            raise ValueError(f"entry {index} corpus is invalid")
        if entry["status"] != "copied":
            raise ValueError(f"entry {index} status must be copied")
        size = entry["size"]
        if type(size) is not int or size < 0:
            raise ValueError(f"entry {index} size must be a non-negative integer")
        digest = entry["sha256"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError(f"entry {index} sha256 is malformed")

        source_absolute = entry["source_absolute"]
        if not isinstance(source_absolute, str) or not source_absolute.strip():
            raise ValueError(f"entry {index} source_absolute must be a non-empty string")
        source_absolute_path = Path(source_absolute)
        if not source_absolute_path.is_absolute():
            raise ValueError(f"entry {index} source_absolute must be absolute")
        source_absolute_key = str(source_absolute_path).casefold()

        source_relative = _relative_path(entry["source_relative"], "source_relative")
        if source_relative.parts[0] != SPEC_BY_TARGET[corpus].source_name:
            raise ValueError(f"entry {index} source_relative has the wrong corpus root")
        source_relative_key = source_relative.as_posix().casefold()

        target_relative = _relative_path(entry["target_relative"], "target_relative")
        target = (target_root / target_relative).resolve()
        private_corpus_root = (
            target_root / "corpus" / "private" / corpus
        ).resolve()
        if target == private_corpus_root or not target.is_relative_to(private_corpus_root):
            raise ValueError(f"entry {index} target is outside private corpus: {target}")
        target_key = str(target).casefold()

        if source_absolute_key in source_absolute_seen:
            raise ValueError(f"duplicate source_absolute in entry {index}")
        if source_relative_key in source_relative_seen:
            raise ValueError(f"duplicate source_relative in entry {index}")
        if target_key in target_seen:
            raise ValueError(f"duplicate target_relative in entry {index}")
        source_absolute_seen.add(source_absolute_key)
        source_relative_seen.add(source_relative_key)
        target_seen.add(target_key)
        expected_targets.add(target)
        expected_target_relatives.add(target_relative.as_posix().casefold())
        entry_counts[corpus] += 1

        if not target.is_file():
            raise ValueError(f"missing migrated file: {target}")
        if sha256_file(target) != digest:
            raise ValueError(f"hash mismatch: {target}")
        if target.stat().st_size != size:
            raise ValueError(f"size mismatch: {target}")

    if dict(entry_counts) != EXPECTED_COUNTS:
        raise ValueError(f"entry corpus_counts mismatch: {dict(entry_counts)}")

    private_root = target_root / "corpus" / "private"
    if not private_root.is_dir():
        raise ValueError(f"missing private corpus directory: {private_root}")
    for corpus in EXPECTED_COUNTS:
        corpus_root = private_root / corpus
        if not corpus_root.is_dir():
            raise ValueError(f"missing private corpus directory: {corpus_root}")
    actual_files = [path for path in private_root.rglob("*") if path.is_file()]
    actual_targets = {path.resolve() for path in actual_files}
    actual_target_relatives = {
        path.relative_to(target_root).as_posix().casefold() for path in actual_files
    }
    missing = expected_targets - actual_targets
    extra = actual_targets - expected_targets
    missing_relatives = expected_target_relatives - actual_target_relatives
    extra_relatives = actual_target_relatives - expected_target_relatives
    if missing or missing_relatives:
        missing_item = (
            sorted(missing_relatives)[0]
            if missing_relatives
            else sorted(str(path) for path in missing)[0]
        )
        raise ValueError(f"missing private file: {missing_item}")
    if extra or extra_relatives:
        extra_item = (
            sorted(extra_relatives)[0]
            if extra_relatives
            else sorted(str(path) for path in extra)[0]
        )
        raise ValueError(f"unexpected private file: {extra_item}")
    return {"verified": len(entries)}


def _inventory_identity(entries: list[dict[str, object]]) -> list[tuple[object, ...]]:
    return [
        (entry["corpus"], entry["source_relative"], entry["target_relative"])
        for entry in entries
    ]


def _reuse_existing_migration(
    source_root: Path,
    target_root: Path,
    manifest_path: Path,
    entries: list[dict[str, object]],
    counts: dict[str, int],
) -> dict[str, object] | None:
    private_root = target_root / "corpus" / "private"
    if not manifest_path.exists() and not private_root.exists():
        return None
    if not manifest_path.is_file() or not private_root.is_dir():
        raise ValueError("destination collision: incomplete migration state")
    try:
        verify_manifest(target_root, manifest_path)
    except ValueError as exc:
        raise ValueError(f"destination collision: {exc}") from exc
    existing = _read_manifest(manifest_path)
    existing_entries = _validate_manifest_shape(existing)
    if existing["source_root"] != str(source_root):
        raise ValueError("source inventory changed: source root differs from manifest")
    if existing["corpus_counts"] != counts or _inventory_identity(existing_entries) != _inventory_identity(entries):
        raise ValueError("source inventory changed from existing manifest")
    if existing_entries != entries:
        raise ValueError("destination collision: source content changed from existing manifest")
    return existing


def _stage_migration(
    source_root: Path,
    target_root: Path,
    manifest: dict[str, object],
) -> tuple[Path, Path]:
    target_root.mkdir(parents=True, exist_ok=True)
    stage_root = Path(tempfile.mkdtemp(prefix=".migration-", dir=target_root))
    stage_manifest = stage_root / "corpus" / "migration-manifest.json"
    try:
        for entry in manifest["entries"]:
            source = source_root / Path(str(entry["source_relative"]))
            destination = stage_root / Path(str(entry["target_relative"]))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if destination.stat().st_size != entry["size"] or sha256_file(destination) != entry["sha256"]:
                raise ValueError(f"copy verification failed: {destination}")
        stage_manifest.parent.mkdir(parents=True, exist_ok=True)
        stage_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        verify_manifest(stage_root, stage_manifest)
        return stage_root, stage_manifest
    except Exception:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise


def migrate_assets(source_root: Path, target_root: Path) -> dict[str, object]:
    source_root = source_root.resolve()
    target_root = target_root.resolve()
    entries, counts = _build_inventory(source_root)
    manifest_path = target_root / "corpus" / "migration-manifest.json"
    existing = _reuse_existing_migration(
        source_root,
        target_root,
        manifest_path,
        entries,
        counts,
    )
    if existing is not None:
        return existing

    manifest: dict[str, object] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "corpus_counts": counts,
        "entries": entries,
    }
    stage_root, stage_manifest = _stage_migration(source_root, target_root, manifest)
    final_private = target_root / "corpus" / "private"
    stage_private = stage_root / "corpus" / "private"
    promoted_private = False
    promoted_manifest = False
    try:
        if final_private.exists() or manifest_path.exists():
            raise ValueError("destination collision: migration state appeared during staging")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        stage_private.replace(final_private)
        promoted_private = True
        stage_manifest.replace(manifest_path)
        promoted_manifest = True
        verify_manifest(target_root, manifest_path)
    except Exception:
        if promoted_manifest and manifest_path.exists():
            manifest_path.unlink()
        if promoted_private and final_private.exists():
            shutil.rmtree(final_private)
        raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate and verify legacy interview assets")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, default=Path.cwd())
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    manifest_path = args.target_root / "corpus" / "migration-manifest.json"
    result = (
        verify_manifest(args.target_root, manifest_path)
        if args.verify_only
        else migrate_assets(args.source_root, args.target_root)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
