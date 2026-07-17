"""Composition root for reliable Bronze ingestion dependencies."""

from pathlib import Path

from lowlands_lens.ingestion.contracts import RetryPolicy
from lowlands_lens.ingestion.filesystem import (
    FilesystemBronzeObjectStore,
    FilesystemCheckpointStore,
    FilesystemQuarantineStore,
    FilesystemRunManifestStore,
)
from lowlands_lens.ingestion.orchestrator import IngestionOrchestrator
from lowlands_lens.ingestion.ports import EuropeanaSource
from lowlands_lens.ingestion.runtime import BlockingSleeper, RandomJitter, SystemClock
from lowlands_lens.ingestion.serialization import Sha256Hasher


def compose_ingestion(
    output_root: Path,
    source: EuropeanaSource,
    *,
    retry_policy: RetryPolicy | None = None,
) -> IngestionOrchestrator:
    """Wire production filesystem/runtime adapters around an injected source."""
    return IngestionOrchestrator(
        source=source,
        object_store=FilesystemBronzeObjectStore(output_root, Sha256Hasher()),
        manifest_store=FilesystemRunManifestStore(output_root),
        checkpoint_store=FilesystemCheckpointStore(output_root),
        quarantine_store=FilesystemQuarantineStore(output_root),
        clock=SystemClock(),
        sleeper=BlockingSleeper(),
        jitter=RandomJitter(),
        retry_policy=RetryPolicy() if retry_policy is None else retry_policy,
    )
