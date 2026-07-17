"""Crash-safe local filesystem adapters for Bronze ingestion."""

import gzip
import hashlib
import json
import os
import re
import uuid
import zlib
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ValidationError

from lowlands_lens.discovery.contracts import RecordRequestConfiguration
from lowlands_lens.ingestion.contracts import (
    QuarantineRecord,
    RunCheckpoint,
    RunManifest,
    StorageOutcome,
    StoredBronzeObject,
)
from lowlands_lens.ingestion.ports import ContentHasher
from lowlands_lens.ingestion.serialization import (
    canonical_json_bytes,
    deterministic_gzip,
)

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_CONTENT_HASH = re.compile(r"^[0-9a-f]{64}$")


class BronzeStorageError(RuntimeError):
    """Base for sanitized immutable-storage failures."""


class BronzeSerializationError(BronzeStorageError):
    """Raised when a source document cannot become canonical JSON."""


class BronzeIntegrityError(BronzeStorageError):
    """Raised when existing immutable evidence is corrupt or colliding."""


class RunStateStorageError(RuntimeError):
    """Raised when durable run state cannot be safely read or written."""


class FilesystemBronzeObjectStore:
    """Content-addressed immutable gzip storage under one output root."""

    def __init__(self, output_root: Path, hasher: ContentHasher) -> None:
        self._output_root = output_root
        self._hasher = hasher

    def store(
        self,
        record_id: str,
        document: Mapping[str, object],
    ) -> StoredBronzeObject:
        """Publish canonical source content or resolve an identical version."""
        validated_id = RecordRequestConfiguration(record_id=record_id).record_id
        try:
            canonical = canonical_json_bytes(document)
        except TypeError, ValueError:
            raise BronzeSerializationError(
                "The sanitized Record document is not canonical JSON data."
            ) from None

        content_hash = self._hasher.hexdigest(canonical)
        if _CONTENT_HASH.fullmatch(content_hash) is None:
            raise BronzeStorageError("The content hasher returned an invalid digest.")

        record_key = hashlib.sha256(validated_id.encode("utf-8")).hexdigest()
        relative_path = (
            Path("bronze")
            / "europeana"
            / "records"
            / record_key
            / "sha256"
            / f"{content_hash}.json.gz"
        )
        final_path = self._output_root / relative_path

        if final_path.exists():
            return self._resolve_existing(
                final_path,
                validated_id,
                content_hash,
                relative_path,
                canonical,
            )

        compressed = deterministic_gzip(canonical)
        created = _publish_new(final_path, compressed)
        if not created:
            return self._resolve_existing(
                final_path,
                validated_id,
                content_hash,
                relative_path,
                canonical,
            )
        return StoredBronzeObject(
            record_id=validated_id,
            content_hash=content_hash,
            relative_path=relative_path.as_posix(),
            outcome=StorageOutcome.CREATED,
            stored_size_bytes=len(compressed),
        )

    def _resolve_existing(
        self,
        final_path: Path,
        record_id: str,
        content_hash: str,
        relative_path: Path,
        expected: bytes,
    ) -> StoredBronzeObject:
        """Verify that a pre-existing immutable path contains identical content."""
        try:
            compressed = final_path.read_bytes()
            actual = gzip.decompress(compressed)
        except OSError, gzip.BadGzipFile, EOFError, zlib.error:
            raise BronzeIntegrityError(
                "Existing Bronze evidence is unreadable or corrupt."
            ) from None
        if actual != expected or self._hasher.hexdigest(actual) != content_hash:
            raise BronzeIntegrityError(
                "Existing Bronze evidence conflicts with its content address."
            )
        return StoredBronzeObject(
            record_id=record_id,
            content_hash=content_hash,
            relative_path=relative_path.as_posix(),
            outcome=StorageOutcome.ALREADY_PRESENT,
            stored_size_bytes=len(compressed),
        )


class FilesystemRunManifestStore:
    """Atomic whole-document persistence for run manifests."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def create(self, manifest: RunManifest) -> None:
        """Create a new run manifest without replacing history."""
        path = self._path(manifest.configuration.run_id)
        if not _publish_new(path, _model_json_bytes(manifest)):
            raise RunStateStorageError("The run manifest already exists.")

    def load(self, run_id: str) -> RunManifest:
        """Load one validated manifest without exposing corrupt content."""
        path = self._path(run_id)
        manifest = _load_model(path, RunManifest, "run manifest")
        if manifest.configuration.run_id != run_id:
            raise RunStateStorageError("The run manifest identity is inconsistent.")
        return manifest

    def save(self, manifest: RunManifest) -> None:
        """Atomically replace mutable manifest state for an existing run."""
        path = self._path(manifest.configuration.run_id)
        if not path.is_file():
            raise RunStateStorageError("The run manifest does not exist.")
        _replace(path, _model_json_bytes(manifest))

    def _path(self, run_id: str) -> Path:
        return self._output_root / "runs" / _safe_identifier(run_id) / "manifest.json"


class FilesystemCheckpointStore:
    """Atomic whole-document persistence for replay checkpoints."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def create(self, checkpoint: RunCheckpoint) -> None:
        """Create the first checkpoint without replacing existing state."""
        path = self._path(checkpoint.run_id)
        if not _publish_new(path, _model_json_bytes(checkpoint)):
            raise RunStateStorageError("The run checkpoint already exists.")

    def load(self, run_id: str) -> RunCheckpoint:
        """Load one validated checkpoint."""
        path = self._path(run_id)
        checkpoint = _load_model(path, RunCheckpoint, "run checkpoint")
        if checkpoint.run_id != run_id:
            raise RunStateStorageError("The run checkpoint identity is inconsistent.")
        return checkpoint

    def save(self, checkpoint: RunCheckpoint) -> None:
        """Atomically replace an existing checkpoint."""
        path = self._path(checkpoint.run_id)
        if not path.is_file():
            raise RunStateStorageError("The run checkpoint does not exist.")
        _replace(path, _model_json_bytes(checkpoint))

    def _path(self, run_id: str) -> Path:
        return self._output_root / "runs" / _safe_identifier(run_id) / "checkpoint.json"


class FilesystemQuarantineStore:
    """Immutable sanitized failure storage scoped to a run."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def store(self, record: QuarantineRecord) -> str:
        """Publish or verify one sanitized failure record."""
        relative_path = (
            Path("runs")
            / _safe_identifier(record.run_id)
            / "quarantine"
            / f"{_safe_identifier(record.request_id)}.json"
        )
        final_path = self._output_root / relative_path
        content = _model_json_bytes(record)
        if final_path.exists():
            try:
                existing = final_path.read_bytes()
            except OSError:
                raise RunStateStorageError(
                    "The quarantine record could not be read."
                ) from None
            if existing != content:
                raise RunStateStorageError(
                    "The quarantine request ID conflicts with existing history."
                )
            return relative_path.as_posix()
        if not _publish_new(final_path, content):
            return self.store(record)
        return relative_path.as_posix()


def _safe_identifier(value: str) -> str:
    """Reject unsafe run and request path segments."""
    if _SAFE_IDENTIFIER.fullmatch(value) is None:
        raise RunStateStorageError("A run-state identifier is invalid.")
    return value


def _model_json_bytes(model: BaseModel) -> bytes:
    """Serialize a validated run-state model for human-readable storage."""
    document = model.model_dump(mode="json")
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _load_model[ModelT: BaseModel](
    path: Path,
    model_type: type[ModelT],
    label: str,
) -> ModelT:
    """Load project-controlled JSON with sanitized diagnostics."""
    try:
        document = json.loads(path.read_bytes())
        return model_type.model_validate(document)
    except OSError, json.JSONDecodeError, UnicodeDecodeError, ValidationError:
        raise RunStateStorageError(
            f"The {label} is missing, corrupt, or invalid."
        ) from None


def _publish_new(path: Path, content: bytes) -> bool:
    """Publish immutable content atomically without replacing a final path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        _write_fsynced(temporary, content)
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False
        _fsync_directory(path.parent)
        return True
    except OSError:
        raise RunStateStorageError(
            "An immutable file could not be published."
        ) from None
    finally:
        temporary.unlink(missing_ok=True)


def _replace(path: Path, content: bytes) -> None:
    """Flush and atomically replace one mutable state document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        _write_fsynced(temporary, content)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except OSError:
        raise RunStateStorageError("Mutable run state could not be saved.") from None
    finally:
        temporary.unlink(missing_ok=True)


def _write_fsynced(path: Path, content: bytes) -> None:
    """Write a new temporary file and flush its bytes to the operating system."""
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    """Best-effort directory flush on platforms that support directory handles."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
