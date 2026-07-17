"""Fault tests for immutable Bronze and atomic run-state storage."""

import gzip
from datetime import UTC, datetime
from pathlib import Path

import pytest

import lowlands_lens.ingestion.filesystem as filesystem_module
from lowlands_lens.ingestion.contracts import (
    RunCheckpoint,
    RunConfiguration,
    RunManifest,
    RunStatus,
    StorageOutcome,
)
from lowlands_lens.ingestion.filesystem import (
    BronzeIntegrityError,
    FilesystemBronzeObjectStore,
    FilesystemCheckpointStore,
    FilesystemRunManifestStore,
    RunStateStorageError,
)
from lowlands_lens.ingestion.serialization import Sha256Hasher, canonical_json_bytes

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


class ConstantHasher:
    """Force deterministic collisions without weakening production hashing."""

    def hexdigest(self, content: bytes) -> str:
        """Return one valid digest for every input."""
        del content
        return "a" * 64


def test_identical_and_changed_content_have_expected_versions(tmp_path: Path) -> None:
    store = FilesystemBronzeObjectStore(tmp_path, Sha256Hasher())
    first_document = {"success": True, "object": {"about": "/dataset/one"}}

    first = store.store("/dataset/one", first_document)
    identical = store.store("/dataset/one", first_document)
    changed = store.store(
        "/dataset/one",
        {"success": True, "object": {"about": "/dataset/one", "revision": 2}},
    )

    assert first.outcome is StorageOutcome.CREATED
    assert identical.outcome is StorageOutcome.ALREADY_PRESENT
    assert identical.relative_path == first.relative_path
    assert changed.outcome is StorageOutcome.CREATED
    assert changed.content_hash != first.content_hash
    assert len(list((tmp_path / "bronze").rglob("*.json.gz"))) == 2

    stored = (tmp_path / first.relative_path).read_bytes()
    assert stored[4:8] == bytes(4)
    assert gzip.decompress(stored) == canonical_json_bytes(first_document)


def test_collision_and_corrupt_existing_files_never_overwrite(tmp_path: Path) -> None:
    collision_store = FilesystemBronzeObjectStore(tmp_path, ConstantHasher())
    first = collision_store.store("/dataset/one", {"value": 1})
    original = (tmp_path / first.relative_path).read_bytes()

    with pytest.raises(BronzeIntegrityError, match="conflicts"):
        collision_store.store("/dataset/one", {"value": 2})
    assert (tmp_path / first.relative_path).read_bytes() == original

    (tmp_path / first.relative_path).write_bytes(b"not-gzip")
    with pytest.raises(BronzeIntegrityError, match="corrupt"):
        collision_store.store("/dataset/one", {"value": 1})
    assert (tmp_path / first.relative_path).read_bytes() == b"not-gzip"


def test_interrupted_temporary_write_never_publishes_final_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FilesystemBronzeObjectStore(tmp_path, Sha256Hasher())

    def fail_after_partial_write(path: Path, content: bytes) -> None:
        path.write_bytes(content[:4])
        raise OSError("synthetic interruption")

    monkeypatch.setattr(filesystem_module, "_write_fsynced", fail_after_partial_write)

    with pytest.raises(RunStateStorageError, match="could not be published"):
        store.store("/dataset/one", {"value": 1})
    assert list(tmp_path.rglob("*.json.gz")) == []
    assert list(tmp_path.rglob("*.tmp")) == []


def test_manifests_and_checkpoints_round_trip_and_reject_recreation(
    tmp_path: Path,
) -> None:
    configuration = RunConfiguration(
        run_id="run-001",
        query_id="war-nl-001",
        candidate_limit=2,
        record_request_limit=2,
        search_page_limit=2,
        output_root=str(tmp_path),
    )
    manifest = RunManifest(
        configuration=configuration,
        status=RunStatus.PLANNED,
        started_at=NOW,
        updated_at=NOW,
    )
    checkpoint = RunCheckpoint(run_id=configuration.run_id, updated_at=NOW)
    manifests = FilesystemRunManifestStore(tmp_path)
    checkpoints = FilesystemCheckpointStore(tmp_path)

    manifests.create(manifest)
    checkpoints.create(checkpoint)

    assert manifests.load(configuration.run_id) == manifest
    assert checkpoints.load(configuration.run_id) == checkpoint
    with pytest.raises(RunStateStorageError, match="already exists"):
        manifests.create(manifest)
    with pytest.raises(RunStateStorageError, match="already exists"):
        checkpoints.create(checkpoint)

    running = manifest.model_copy(update={"status": RunStatus.RUNNING})
    manifests.save(running)
    assert manifests.load(configuration.run_id).status is RunStatus.RUNNING
