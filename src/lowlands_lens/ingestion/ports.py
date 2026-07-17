"""Ports required by the Bronze ingestion application layer."""

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Protocol, TypeVar

from lowlands_lens.discovery.client import EuropeanaRecordSnapshot
from lowlands_lens.discovery.contracts import (
    EuropeanaSearchResponsePayload,
    RecordRequestConfiguration,
    SearchRequestConfiguration,
)
from lowlands_lens.ingestion.contracts import (
    QuarantineRecord,
    RunCheckpoint,
    RunManifest,
    StoredBronzeObject,
)

ResultT = TypeVar("ResultT")


class EuropeanaSource(Protocol):
    """Search and Record capability already supplied by the Phase 3 client."""

    def search(
        self,
        request: SearchRequestConfiguration,
    ) -> EuropeanaSearchResponsePayload:
        """Return one bounded Search page."""
        ...

    def record_snapshot(
        self,
        request: RecordRequestConfiguration,
    ) -> EuropeanaRecordSnapshot:
        """Return one validated, recursively sanitized Record snapshot."""
        ...


class BronzeObjectStore(Protocol):
    """Content-addressed immutable source-document storage."""

    def store(
        self,
        record_id: str,
        document: Mapping[str, object],
    ) -> StoredBronzeObject:
        """Publish or resolve one sanitized Record version."""
        ...


class RunManifestStore(Protocol):
    """Atomic persistence for complete run manifests."""

    def create(self, manifest: RunManifest) -> None:
        """Create a manifest without replacing an existing run."""
        ...

    def load(self, run_id: str) -> RunManifest:
        """Load and validate an existing manifest."""
        ...

    def save(self, manifest: RunManifest) -> None:
        """Atomically replace mutable run state."""
        ...


class CheckpointStore(Protocol):
    """Atomic persistence for replay checkpoints."""

    def create(self, checkpoint: RunCheckpoint) -> None:
        """Create the first checkpoint for a run."""
        ...

    def load(self, run_id: str) -> RunCheckpoint:
        """Load and validate the current checkpoint."""
        ...

    def save(self, checkpoint: RunCheckpoint) -> None:
        """Atomically advance a checkpoint."""
        ...


class QuarantineStore(Protocol):
    """Immutable sanitized terminal-failure storage."""

    def store(self, record: QuarantineRecord) -> str:
        """Publish a failure and return its output-root-relative path."""
        ...


class Clock(Protocol):
    """Timezone-aware source of current time."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        ...


class Sleeper(Protocol):
    """Delay execution between retry attempts."""

    def sleep(self, seconds: float) -> None:
        """Wait for the requested non-negative duration."""
        ...


class JitterSource(Protocol):
    """Deterministic-testable source of retry jitter fractions."""

    def fraction(self) -> float:
        """Return a value from zero through one."""
        ...


class ContentHasher(Protocol):
    """Content digest capability used by immutable storage."""

    def hexdigest(self, content: bytes) -> str:
        """Return a lowercase digest for the supplied bytes."""
        ...


class AttemptObserver(Protocol):
    """Durably reserve a provider call before it is attempted."""

    def __call__(self) -> None:
        """Reserve one call or raise when its global budget is exhausted."""
        ...


Operation = Callable[[], ResultT]
