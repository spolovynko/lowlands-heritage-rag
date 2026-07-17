"""Credential-free end-to-end fault tests for Phase 4 ingestion."""

import gzip
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from lowlands_lens.discovery.client import (
    EuropeanaDiscoveryClient,
    EuropeanaRecordNotFoundError,
    EuropeanaRecordSnapshot,
    EuropeanaTimeoutError,
)
from lowlands_lens.discovery.configuration import EuropeanaCredentials
from lowlands_lens.discovery.contracts import (
    EuropeanaRecordResponsePayload,
    EuropeanaSearchResponsePayload,
    RecordRequestConfiguration,
    SearchRequestConfiguration,
)
from lowlands_lens.discovery.transport import HttpResponse
from lowlands_lens.ingestion.contracts import (
    RequestKind,
    RetryPolicy,
    RunCheckpoint,
    RunConfiguration,
    RunStatus,
    StoredBronzeObject,
)
from lowlands_lens.ingestion.filesystem import (
    FilesystemBronzeObjectStore,
    FilesystemCheckpointStore,
    FilesystemQuarantineStore,
    FilesystemRunManifestStore,
)
from lowlands_lens.ingestion.orchestrator import IngestionOrchestrator
from lowlands_lens.ingestion.ports import BronzeObjectStore, CheckpointStore
from lowlands_lens.ingestion.serialization import Sha256Hasher

FAKE_SECRET = "phase4-fake-secret-that-must-not-appear"


class IncrementingClock:
    """Return deterministic increasing UTC timestamps."""

    def __init__(self) -> None:
        self.current = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


class NoSleep:
    """Accept only zero-delay deterministic test retries."""

    def sleep(self, seconds: float) -> None:
        assert seconds == 0


class ZeroJitter:
    """Remove randomness from retry calculations."""

    def fraction(self) -> float:
        return 0.0


class FakeEuropeanaSource:
    """Serve deterministic Search pages and sanitized Record snapshots."""

    def __init__(
        self,
        pages: dict[str, EuropeanaSearchResponsePayload],
        snapshots: dict[str, EuropeanaRecordSnapshot],
        *,
        errors: dict[str, Exception] | None = None,
        interrupt_on_record_call: int | None = None,
    ) -> None:
        self.pages = pages
        self.snapshots = snapshots
        self.errors = {} if errors is None else errors
        self.interrupt_on_record_call = interrupt_on_record_call
        self.search_requests: list[SearchRequestConfiguration] = []
        self.record_requests: list[RecordRequestConfiguration] = []

    def search(
        self,
        request: SearchRequestConfiguration,
    ) -> EuropeanaSearchResponsePayload:
        self.search_requests.append(request)
        assert request.cursor is not None
        return self.pages[request.cursor]

    def record_snapshot(
        self,
        request: RecordRequestConfiguration,
    ) -> EuropeanaRecordSnapshot:
        self.record_requests.append(request)
        if len(self.record_requests) == self.interrupt_on_record_call:
            self.interrupt_on_record_call = None
            raise KeyboardInterrupt
        error = self.errors.get(request.record_id)
        if error is not None:
            raise error
        return self.snapshots[request.record_id]


class QueueTransport:
    """Return queued provider documents while capturing secret-bearing headers."""

    def __init__(self, documents: list[dict[str, object]]) -> None:
        self.documents = list(documents)
        self.headers: list[Mapping[str, str]] = []

    def get(
        self,
        url: str,
        *,
        params: Sequence[tuple[str, str]],
        headers: Mapping[str, str],
    ) -> HttpResponse:
        del url, params
        self.headers.append(headers)
        document = self.documents.pop(0)
        return HttpResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            content=json.dumps(document).encode("utf-8"),
        )


class InterruptAfterStore:
    """Publish evidence once, then interrupt before the manifest entry."""

    def __init__(self, delegate: FilesystemBronzeObjectStore) -> None:
        self.delegate = delegate
        self.interrupted = False

    def store(
        self,
        record_id: str,
        document: Mapping[str, object],
    ) -> StoredBronzeObject:
        stored = self.delegate.store(record_id, document)
        if not self.interrupted:
            self.interrupted = True
            raise KeyboardInterrupt
        return stored


class InterruptBeforeRecordCheckpoint:
    """Interrupt after a Record manifest entry but before checkpoint advance."""

    def __init__(self, delegate: FilesystemCheckpointStore) -> None:
        self.delegate = delegate
        self.interrupted = False

    def create(self, checkpoint: RunCheckpoint) -> None:
        self.delegate.create(checkpoint)

    def load(self, run_id: str) -> RunCheckpoint:
        return self.delegate.load(run_id)

    def save(self, checkpoint: RunCheckpoint) -> None:
        if checkpoint.next_record_index == 1 and not self.interrupted:
            self.interrupted = True
            raise KeyboardInterrupt
        self.delegate.save(checkpoint)


def search_response(
    ids: list[str],
    next_cursor: str | None,
) -> EuropeanaSearchResponsePayload:
    """Build one synthetic provider Search page."""
    return EuropeanaSearchResponsePayload.model_validate(
        {
            "success": True,
            "itemsCount": len(ids),
            "totalResults": 3,
            "nextCursor": next_cursor,
            "items": [{"id": record_id} for record_id in ids],
        }
    )


def snapshot(record_id: str, revision: int = 1) -> EuropeanaRecordSnapshot:
    """Build a complete sanitized source-shaped Record snapshot."""
    document: dict[str, object] = {
        "success": True,
        "object": {
            "about": record_id,
            "proxies": [
                {
                    "about": f"/proxy{record_id}",
                    "dcTitle": {"nl": [f"Synthetisch record {record_id}"]},
                    "dcDescription": {"def": [f"Revision {revision}"]},
                }
            ],
            "aggregations": [
                {
                    "edmProvider": {"def": ["Synthetic Provider"]},
                    "edmIsShownAt": f"https://example.invalid{record_id}",
                }
            ],
        },
        "apikey": "<redacted>",
        "unknownFutureField": {"revision": revision},
    }
    return EuropeanaRecordSnapshot(
        parsed=EuropeanaRecordResponsePayload.model_validate(document),
        sanitized_document=document,
    )


def pages_for(ids: list[str]) -> dict[str, EuropeanaSearchResponsePayload]:
    """Return one or two cursor pages with a deliberate duplicate ID."""
    if len(ids) <= 2:
        return {"*": search_response(ids, None)}
    return {
        "*": search_response(ids[:2], "cursor-2"),
        "cursor-2": search_response([ids[1], *ids[2:]], None),
    }


def request() -> SearchRequestConfiguration:
    """Return the approved query without pagination state."""
    return SearchRequestConfiguration(
        query_id="war-nl-001",
        query="België Eerste Wereldoorlog herdenking",
        facets=("TYPE",),
        rows=2,
        sample_limit=2,
    )


def configuration(
    root: Path,
    run_id: str,
    *,
    candidates: int,
    record_requests: int,
    search_pages: int,
) -> RunConfiguration:
    """Return one approved test-only run configuration."""
    return RunConfiguration(
        run_id=run_id,
        query_id="war-nl-001",
        candidate_limit=candidates,
        record_request_limit=record_requests,
        search_page_limit=search_pages,
        output_root=str(root),
    )


def orchestrator(
    root: Path,
    source: FakeEuropeanaSource,
    *,
    object_store: BronzeObjectStore | None = None,
    checkpoint_store: CheckpointStore | None = None,
) -> IngestionOrchestrator:
    """Compose filesystem adapters with deterministic runtime fakes."""
    objects = (
        FilesystemBronzeObjectStore(root, Sha256Hasher())
        if object_store is None
        else object_store
    )
    checkpoints = (
        FilesystemCheckpointStore(root)
        if checkpoint_store is None
        else checkpoint_store
    )
    return IngestionOrchestrator(
        source=source,
        object_store=objects,
        manifest_store=FilesystemRunManifestStore(root),
        checkpoint_store=checkpoints,
        quarantine_store=FilesystemQuarantineStore(root),
        clock=IncrementingClock(),
        sleeper=NoSleep(),
        jitter=ZeroJitter(),
        retry_policy=RetryPolicy(
            max_attempts=2,
            base_delay_seconds=0,
            max_delay_seconds=0,
            max_total_delay_seconds=0,
            jitter_ratio=0,
        ),
    )


def test_identical_rerun_changed_version_traceability_and_secret_scan(
    tmp_path: Path,
) -> None:
    ids = ["/dataset/one", "/dataset/two", "/dataset/three"]
    original = {record_id: snapshot(record_id) for record_id in ids}

    first_source = FakeEuropeanaSource(pages_for(ids), original)
    first = orchestrator(tmp_path, first_source).execute(
        configuration(
            tmp_path,
            "run-001",
            candidates=3,
            record_requests=3,
            search_pages=3,
        ),
        request(),
    )
    second_source = FakeEuropeanaSource(pages_for(ids), original)
    second = orchestrator(tmp_path, second_source).execute(
        configuration(
            tmp_path,
            "run-002",
            candidates=3,
            record_requests=3,
            search_pages=3,
        ),
        request(),
    )

    changed_snapshots = dict(original)
    changed_snapshots["/dataset/two"] = snapshot("/dataset/two", revision=2)
    third_source = FakeEuropeanaSource(pages_for(ids), changed_snapshots)
    third = orchestrator(tmp_path, third_source).execute(
        configuration(
            tmp_path,
            "run-003",
            candidates=3,
            record_requests=3,
            search_pages=3,
        ),
        request(),
    )

    assert first.status is RunStatus.COMPLETED
    assert first.created_count == 3
    assert second.created_count == 0
    assert second.existing_count == 3
    assert third.created_count == 1
    assert third.existing_count == 2

    raw_paths = {
        path.relative_to(tmp_path).as_posix()
        for path in (tmp_path / "bronze").rglob("*.json.gz")
    }
    traced_paths = {
        entry.storage_path
        for manifest in (first, second, third)
        for entry in manifest.entries
        if entry.kind is RequestKind.RECORD and entry.storage_path is not None
    }
    assert len(raw_paths) == 4
    assert raw_paths <= traced_paths

    for manifest in (first, second, third):
        for entry in manifest.entries:
            if entry.kind is not RequestKind.RECORD or entry.storage_path is None:
                continue
            canonical = gzip.decompress((tmp_path / entry.storage_path).read_bytes())
            assert hashlib.sha256(canonical).hexdigest() == entry.content_hash

    for path in (tmp_path / "runs").rglob("*.json"):
        assert FAKE_SECRET.encode() not in path.read_bytes()
    for path in (tmp_path / "bronze").rglob("*.json.gz"):
        assert FAKE_SECRET.encode() not in gzip.decompress(path.read_bytes())


def test_permanent_failure_is_quarantined_without_original_message(
    tmp_path: Path,
) -> None:
    ids = ["/dataset/one", "/dataset/missing"]
    source = FakeEuropeanaSource(
        pages_for(ids),
        {"/dataset/one": snapshot("/dataset/one")},
        errors={
            "/dataset/missing": EuropeanaRecordNotFoundError(FAKE_SECRET),
        },
    )
    manifest = orchestrator(tmp_path, source).execute(
        configuration(
            tmp_path,
            "run-quarantine",
            candidates=2,
            record_requests=2,
            search_pages=1,
        ),
        request(),
    )

    assert manifest.status is RunStatus.COMPLETED
    assert manifest.created_count == 1
    assert manifest.quarantined_count == 1
    failure_entry = next(
        entry for entry in manifest.entries if entry.failure is not None
    )
    assert failure_entry.quarantine_path is not None
    quarantine_bytes = (tmp_path / failure_entry.quarantine_path).read_bytes()
    assert FAKE_SECRET.encode() not in quarantine_bytes
    assert b"response" not in quarantine_bytes.lower()


def test_real_client_redacts_provider_and_header_secret_before_bronze(
    tmp_path: Path,
) -> None:
    record_id = "/dataset/one"
    search_document: dict[str, object] = {
        "success": True,
        "itemsCount": 1,
        "totalResults": 1,
        "items": [{"id": record_id}],
        "apikey": FAKE_SECRET,
    }
    record_document: dict[str, object] = {
        "success": True,
        "apikey": FAKE_SECRET,
        "object": {
            "about": record_id,
            "proxies": [
                {
                    "about": "/proxy/dataset/one",
                    "dcTitle": {"nl": ["Synthetisch record"]},
                    "nested": {"X-Api-Key": FAKE_SECRET},
                }
            ],
            "aggregations": [],
        },
    }
    transport = QueueTransport([search_document, record_document])
    client = EuropeanaDiscoveryClient(
        transport,
        EuropeanaCredentials(api_key=FAKE_SECRET),
    )

    manifest = compose_real_client(tmp_path, client).execute(
        configuration(
            tmp_path,
            "run-real-client",
            candidates=1,
            record_requests=1,
            search_pages=1,
        ),
        request(),
    )

    assert manifest.created_count == 1
    assert transport.headers[0]["X-Api-Key"] == FAKE_SECRET
    for path in tmp_path.rglob("*"):
        if not path.is_file():
            continue
        content = path.read_bytes()
        if path.suffix == ".gz":
            content = gzip.decompress(content)
        assert FAKE_SECRET.encode() not in content


def compose_real_client(
    root: Path,
    client: EuropeanaDiscoveryClient,
) -> IngestionOrchestrator:
    """Prove the existing concrete client satisfies the new source protocol."""
    return IngestionOrchestrator(
        source=client,
        object_store=FilesystemBronzeObjectStore(root, Sha256Hasher()),
        manifest_store=FilesystemRunManifestStore(root),
        checkpoint_store=FilesystemCheckpointStore(root),
        quarantine_store=FilesystemQuarantineStore(root),
        clock=IncrementingClock(),
        sleeper=NoSleep(),
        jitter=ZeroJitter(),
        retry_policy=RetryPolicy(max_attempts=1),
    )


def test_interrupted_record_request_resumes_from_durable_checkpoint(
    tmp_path: Path,
) -> None:
    ids = ["/dataset/one", "/dataset/two"]
    snapshots = {record_id: snapshot(record_id) for record_id in ids}
    source = FakeEuropeanaSource(
        pages_for(ids),
        snapshots,
        interrupt_on_record_call=2,
    )
    config = configuration(
        tmp_path,
        "run-interrupted",
        candidates=2,
        record_requests=3,
        search_pages=1,
    )
    runner = orchestrator(tmp_path, source)

    with pytest.raises(KeyboardInterrupt):
        runner.execute(config, request())
    interrupted = FilesystemRunManifestStore(tmp_path).load(config.run_id)
    checkpoint = FilesystemCheckpointStore(tmp_path).load(config.run_id)
    assert interrupted.status is RunStatus.INTERRUPTED
    assert checkpoint.next_record_index == 1

    completed = orchestrator(tmp_path, source).execute(
        config,
        request(),
        resume=True,
    )
    assert completed.status is RunStatus.COMPLETED
    assert completed.created_count == 2
    assert completed.record_request_count == 3
    assert len(list((tmp_path / "bronze").rglob("*.json.gz"))) == 2


def test_resume_after_storage_before_manifest_resolves_existing_object(
    tmp_path: Path,
) -> None:
    record_id = "/dataset/one"
    source = FakeEuropeanaSource(
        pages_for([record_id]),
        {record_id: snapshot(record_id)},
    )
    config = configuration(
        tmp_path,
        "run-after-storage",
        candidates=1,
        record_requests=2,
        search_pages=1,
    )
    base_store = FilesystemBronzeObjectStore(tmp_path, Sha256Hasher())
    interrupting = InterruptAfterStore(base_store)

    with pytest.raises(KeyboardInterrupt):
        orchestrator(tmp_path, source, object_store=interrupting).execute(
            config,
            request(),
        )
    assert len(list((tmp_path / "bronze").rglob("*.json.gz"))) == 1

    completed = orchestrator(tmp_path, source, object_store=base_store).execute(
        config,
        request(),
        resume=True,
    )
    assert completed.created_count == 0
    assert completed.existing_count == 1
    assert completed.record_request_count == 2
    assert len(list((tmp_path / "bronze").rglob("*.json.gz"))) == 1


def test_resume_reconciles_manifest_before_checkpoint_without_source_replay(
    tmp_path: Path,
) -> None:
    record_id = "/dataset/one"
    source = FakeEuropeanaSource(
        pages_for([record_id]),
        {record_id: snapshot(record_id)},
    )
    config = configuration(
        tmp_path,
        "run-before-checkpoint",
        candidates=1,
        record_requests=1,
        search_pages=1,
    )
    base_checkpoints = FilesystemCheckpointStore(tmp_path)
    interrupting = InterruptBeforeRecordCheckpoint(base_checkpoints)

    with pytest.raises(KeyboardInterrupt):
        orchestrator(
            tmp_path,
            source,
            checkpoint_store=interrupting,
        ).execute(config, request())
    assert len(source.record_requests) == 1
    assert base_checkpoints.load(config.run_id).next_record_index == 0

    completed = orchestrator(tmp_path, source).execute(
        config,
        request(),
        resume=True,
    )
    assert completed.status is RunStatus.COMPLETED
    assert completed.created_count == 1
    assert completed.record_request_count == 1
    assert len(source.record_requests) == 1


def test_selected_retryable_quarantine_recovery_creates_new_run(
    tmp_path: Path,
) -> None:
    record_id = "/dataset/one"
    failing_source = FakeEuropeanaSource(
        pages_for([record_id]),
        {},
        errors={record_id: EuropeanaTimeoutError(FAKE_SECRET)},
    )
    original_config = configuration(
        tmp_path,
        "run-retryable-failure",
        candidates=1,
        record_requests=2,
        search_pages=1,
    )
    original = orchestrator(tmp_path, failing_source).execute(
        original_config,
        request(),
    )
    failed_entry = next(
        entry for entry in original.entries if entry.failure is not None
    )
    assert original.quarantined_count == 1
    assert failed_entry.failure is not None
    assert failed_entry.failure.retryable is True

    healthy_source = FakeEuropeanaSource(
        pages_for([record_id]),
        {record_id: snapshot(record_id)},
    )
    recovery_config = RunConfiguration(
        run_id="run-recovery-001",
        query_id="war-nl-001",
        candidate_limit=1,
        record_request_limit=1,
        search_page_limit=1,
        output_root=str(tmp_path),
        recovery_of_run_id=original_config.run_id,
        selected_failure_request_ids=(failed_entry.request_id,),
    )
    recovered = orchestrator(tmp_path, healthy_source).execute_recovery(
        recovery_config,
        original,
    )

    assert recovered.status is RunStatus.COMPLETED
    assert recovered.created_count == 1
    assert recovered.configuration.recovery_of_run_id == original_config.run_id
    assert healthy_source.search_requests == []
    assert len(healthy_source.record_requests) == 1
    assert FilesystemRunManifestStore(tmp_path).load(original_config.run_id) == original
