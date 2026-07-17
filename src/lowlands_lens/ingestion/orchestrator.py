"""Sequential, restartable Bronze ingestion orchestration."""

from dataclasses import dataclass
from functools import partial

from lowlands_lens.discovery.contracts import (
    RecordRequestConfiguration,
    SearchRequestConfiguration,
)
from lowlands_lens.ingestion.contracts import (
    FailureDetail,
    ManifestEntry,
    ManifestOutcome,
    QuarantineRecord,
    RequestKind,
    RetryPolicy,
    RunCheckpoint,
    RunConfiguration,
    RunManifest,
    RunStatus,
    StorageOutcome,
)
from lowlands_lens.ingestion.pagination import advance_cursor, build_cursor_request
from lowlands_lens.ingestion.ports import (
    BronzeObjectStore,
    CheckpointStore,
    Clock,
    EuropeanaSource,
    JitterSource,
    QuarantineStore,
    RunManifestStore,
    Sleeper,
)
from lowlands_lens.ingestion.retry import (
    AttemptBudgetExhaustedError,
    OperationFailedError,
    classify_failure,
    execute_with_retry,
)


class IngestionConfigurationError(ValueError):
    """Raised before source access when a run configuration is inconsistent."""


class IngestionRunError(RuntimeError):
    """Sanitized failure of a complete ingestion run."""


class IngestionInterruptedError(RuntimeError):
    """Explicit safe interruption used by operations and recovery tests."""


@dataclass(slots=True)
class IngestionOrchestrator:
    """Coordinate bounded Search, Record capture, and durable replay state."""

    source: EuropeanaSource
    object_store: BronzeObjectStore
    manifest_store: RunManifestStore
    checkpoint_store: CheckpointStore
    quarantine_store: QuarantineStore
    clock: Clock
    sleeper: Sleeper
    jitter: JitterSource
    retry_policy: RetryPolicy

    def execute(
        self,
        configuration: RunConfiguration,
        search_request: SearchRequestConfiguration,
        *,
        resume: bool = False,
    ) -> RunManifest:
        """Execute or resume one sequential run within persisted hard limits."""
        self._validate_before_access(configuration, search_request)
        if resume:
            manifest, checkpoint = self._load_for_resume(configuration)
        else:
            manifest, checkpoint = self._create_run(configuration)

        manifest = _replace_manifest(
            manifest,
            status=RunStatus.RUNNING,
            updated_at=self.clock.now(),
            finished_at=None,
        )
        self.manifest_store.save(manifest)

        try:
            manifest, checkpoint = self._collect_candidates(
                manifest,
                checkpoint,
                search_request,
            )
            manifest, checkpoint = self._capture_records(manifest, checkpoint)
            completed_at = self.clock.now()
            manifest = _replace_manifest(
                manifest,
                status=RunStatus.COMPLETED,
                updated_at=completed_at,
                finished_at=completed_at,
            )
            self.manifest_store.save(manifest)
            return manifest
        except KeyboardInterrupt, IngestionInterruptedError:
            interrupted_at = self.clock.now()
            current = self.manifest_store.load(configuration.run_id)
            interrupted = _replace_manifest(
                current,
                status=RunStatus.INTERRUPTED,
                updated_at=interrupted_at,
                finished_at=interrupted_at,
            )
            self.manifest_store.save(interrupted)
            raise
        except Exception:
            failed_at = self.clock.now()
            current = self.manifest_store.load(configuration.run_id)
            failed = _replace_manifest(
                current,
                status=RunStatus.FAILED,
                updated_at=failed_at,
                finished_at=failed_at,
            )
            try:
                self.manifest_store.save(failed)
            except Exception:
                pass
            raise

    def execute_recovery(
        self,
        configuration: RunConfiguration,
        source_manifest: RunManifest,
    ) -> RunManifest:
        """Retry explicitly selected retryable failures in a new bounded run."""
        if configuration.recovery_of_run_id != source_manifest.configuration.run_id:
            raise IngestionConfigurationError(
                "The recovery source does not match the persisted configuration."
            )
        selected_entries: list[ManifestEntry] = []
        for request_id in configuration.selected_failure_request_ids:
            entry = _entry_by_request_id(source_manifest, request_id)
            if (
                entry is None
                or entry.outcome is not ManifestOutcome.QUARANTINED
                or entry.record_id is None
                or entry.failure is None
                or not entry.failure.retryable
            ):
                raise IngestionConfigurationError(
                    "Recovery selection contains an ineligible failure."
                )
            selected_entries.append(entry)
        if not selected_entries:
            raise IngestionConfigurationError("Recovery requires selected failures.")
        if len(selected_entries) > configuration.candidate_limit:
            raise IngestionConfigurationError(
                "Recovery selection exceeds the candidate limit."
            )

        manifest, checkpoint = self._create_run(configuration)
        now = self.clock.now()
        manifest = _replace_manifest(
            manifest,
            status=RunStatus.RUNNING,
            candidate_count=len(selected_entries),
            updated_at=now,
        )
        self.manifest_store.save(manifest)
        checkpoint = _replace_checkpoint(
            checkpoint,
            candidate_record_ids=tuple(entry.record_id for entry in selected_entries),
            next_cursor=None,
            search_complete=True,
            updated_at=now,
        )
        self.checkpoint_store.save(checkpoint)

        try:
            manifest, checkpoint = self._capture_records(manifest, checkpoint)
            completed_at = self.clock.now()
            manifest = _replace_manifest(
                manifest,
                status=RunStatus.COMPLETED,
                updated_at=completed_at,
                finished_at=completed_at,
            )
            self.manifest_store.save(manifest)
            return manifest
        except KeyboardInterrupt, IngestionInterruptedError:
            interrupted_at = self.clock.now()
            current = self.manifest_store.load(configuration.run_id)
            interrupted = _replace_manifest(
                current,
                status=RunStatus.INTERRUPTED,
                updated_at=interrupted_at,
                finished_at=interrupted_at,
            )
            self.manifest_store.save(interrupted)
            raise
        except Exception:
            failed_at = self.clock.now()
            current = self.manifest_store.load(configuration.run_id)
            failed = _replace_manifest(
                current,
                status=RunStatus.FAILED,
                updated_at=failed_at,
                finished_at=failed_at,
            )
            try:
                self.manifest_store.save(failed)
            except Exception:
                pass
            raise

    def _validate_before_access(
        self,
        configuration: RunConfiguration,
        search_request: SearchRequestConfiguration,
    ) -> None:
        """Reject conflicting source selection before any dependency call."""
        if search_request.query_id != configuration.query_id:
            raise IngestionConfigurationError(
                "The Search request does not match the approved query ID."
            )
        if search_request.start is not None or search_request.cursor is not None:
            raise IngestionConfigurationError(
                "The base Search request cannot contain pagination state."
            )

    def _create_run(
        self,
        configuration: RunConfiguration,
    ) -> tuple[RunManifest, RunCheckpoint]:
        """Create planned state before the first source request."""
        now = self.clock.now()
        manifest = RunManifest(
            configuration=configuration,
            status=RunStatus.PLANNED,
            started_at=now,
            updated_at=now,
        )
        checkpoint = RunCheckpoint(run_id=configuration.run_id, updated_at=now)
        self.manifest_store.create(manifest)
        self.checkpoint_store.create(checkpoint)
        return manifest, checkpoint

    def _load_for_resume(
        self,
        configuration: RunConfiguration,
    ) -> tuple[RunManifest, RunCheckpoint]:
        """Load durable state and prevent configuration drift."""
        manifest = self.manifest_store.load(configuration.run_id)
        checkpoint = self.checkpoint_store.load(configuration.run_id)
        if manifest.configuration != configuration:
            raise IngestionConfigurationError(
                "Resume configuration differs from the persisted run."
            )
        if checkpoint.run_id != configuration.run_id:
            raise IngestionConfigurationError("Checkpoint run ID is inconsistent.")
        if manifest.status is RunStatus.COMPLETED:
            raise IngestionConfigurationError("Completed runs cannot be resumed.")
        return manifest, checkpoint

    def _collect_candidates(
        self,
        manifest: RunManifest,
        checkpoint: RunCheckpoint,
        base_request: SearchRequestConfiguration,
    ) -> tuple[RunManifest, RunCheckpoint]:
        """Resume-safe cursor traversal with independent ID deduplication."""
        while not checkpoint.search_complete:
            request_id = f"search-page-{len(checkpoint.seen_cursors) + 1:04d}"
            existing = _entry_by_request_id(manifest, request_id)
            if existing is not None:
                checkpoint = self._reconcile_search_entry(
                    manifest,
                    checkpoint,
                    existing,
                )
                self.checkpoint_store.save(checkpoint)
                continue

            request = build_cursor_request(
                base_request,
                checkpoint,
                manifest.configuration.candidate_limit,
            )

            def reserve_search_attempt() -> None:
                nonlocal manifest
                if (
                    manifest.search_request_count
                    >= manifest.configuration.search_page_limit
                ):
                    raise AttemptBudgetExhaustedError(
                        "The Search request budget is exhausted."
                    )
                manifest = _replace_manifest(
                    manifest,
                    search_request_count=manifest.search_request_count + 1,
                    updated_at=self.clock.now(),
                )
                self.manifest_store.save(manifest)

            try:
                retried = execute_with_retry(
                    partial(self.source.search, request),
                    policy=self.retry_policy,
                    sleeper=self.sleeper,
                    jitter=self.jitter,
                    before_attempt=reserve_search_attempt,
                )
            except AttemptBudgetExhaustedError:
                checkpoint = _replace_checkpoint(
                    checkpoint,
                    search_complete=True,
                    next_cursor=None,
                    updated_at=self.clock.now(),
                )
                self.checkpoint_store.save(checkpoint)
                break
            except OperationFailedError as error:
                raise IngestionRunError(error.failure.message) from None

            advance = advance_cursor(
                checkpoint,
                retried.value,
                candidate_limit=manifest.configuration.candidate_limit,
                completed_page_count=manifest.search_request_count,
                page_limit=manifest.configuration.search_page_limit,
                updated_at=self.clock.now(),
            )
            entry = ManifestEntry(
                request_id=request_id,
                kind=RequestKind.SEARCH,
                occurred_at=self.clock.now(),
                attempts=retried.attempts,
                outcome=ManifestOutcome.PAGE_CAPTURED,
                cursor=advance.request_cursor,
                next_cursor=advance.checkpoint.next_cursor,
                candidate_ids=advance.new_candidate_ids,
            )
            manifest = _append_entry(
                manifest,
                entry,
                candidate_count=len(advance.checkpoint.candidate_record_ids),
                updated_at=self.clock.now(),
            )
            self.manifest_store.save(manifest)
            checkpoint = advance.checkpoint
            self.checkpoint_store.save(checkpoint)
        return manifest, checkpoint

    def _reconcile_search_entry(
        self,
        manifest: RunManifest,
        checkpoint: RunCheckpoint,
        entry: ManifestEntry,
    ) -> RunCheckpoint:
        """Advance a lagging cursor checkpoint from durable manifest evidence."""
        if entry.cursor != checkpoint.next_cursor:
            raise IngestionRunError("Search manifest and checkpoint disagree.")
        ids = list(checkpoint.candidate_record_ids)
        known = set(ids)
        for record_id in entry.candidate_ids:
            if record_id not in known:
                known.add(record_id)
                ids.append(record_id)
        seen = (*checkpoint.seen_cursors, entry.cursor)
        complete = (
            entry.next_cursor is None
            or entry.next_cursor in seen
            or len(ids) >= manifest.configuration.candidate_limit
            or manifest.search_request_count >= manifest.configuration.search_page_limit
        )
        return _replace_checkpoint(
            checkpoint,
            candidate_record_ids=tuple(ids),
            seen_cursors=seen,
            next_cursor=None if complete else entry.next_cursor,
            search_complete=complete,
            updated_at=self.clock.now(),
        )

    def _capture_records(
        self,
        manifest: RunManifest,
        checkpoint: RunCheckpoint,
    ) -> tuple[RunManifest, RunCheckpoint]:
        """Retrieve, store, quarantine, and checkpoint candidate Records."""
        while checkpoint.next_record_index < len(checkpoint.candidate_record_ids):
            index = checkpoint.next_record_index
            record_id = checkpoint.candidate_record_ids[index]
            request_id = f"record-{index + 1:04d}"
            existing = _entry_by_request_id(manifest, request_id)
            if existing is not None:
                checkpoint = _replace_checkpoint(
                    checkpoint,
                    next_record_index=index + 1,
                    updated_at=self.clock.now(),
                )
                self.checkpoint_store.save(checkpoint)
                continue
            if (
                manifest.record_request_count
                >= manifest.configuration.record_request_limit
            ):
                break

            def reserve_record_attempt() -> None:
                nonlocal manifest
                if (
                    manifest.record_request_count
                    >= manifest.configuration.record_request_limit
                ):
                    raise AttemptBudgetExhaustedError(
                        "The Record request budget is exhausted."
                    )
                manifest = _replace_manifest(
                    manifest,
                    record_request_count=manifest.record_request_count + 1,
                    updated_at=self.clock.now(),
                )
                self.manifest_store.save(manifest)

            try:
                retried = execute_with_retry(
                    partial(
                        self.source.record_snapshot,
                        RecordRequestConfiguration(record_id=record_id),
                    ),
                    policy=self.retry_policy,
                    sleeper=self.sleeper,
                    jitter=self.jitter,
                    before_attempt=reserve_record_attempt,
                )
            except AttemptBudgetExhaustedError:
                break
            except OperationFailedError as error:
                manifest, checkpoint = self._quarantine(
                    manifest,
                    checkpoint,
                    request_id=request_id,
                    record_id=record_id,
                    attempts=error.attempts,
                    failure=error.failure,
                )
                continue

            try:
                stored = self.object_store.store(
                    record_id,
                    retried.value.sanitized_document,
                )
            except Exception as error:
                manifest, checkpoint = self._quarantine(
                    manifest,
                    checkpoint,
                    request_id=request_id,
                    record_id=record_id,
                    attempts=retried.attempts,
                    failure=classify_failure(error),
                )
                continue

            outcome = (
                ManifestOutcome.CREATED
                if stored.outcome is StorageOutcome.CREATED
                else ManifestOutcome.ALREADY_PRESENT
            )
            entry = ManifestEntry(
                request_id=request_id,
                kind=RequestKind.RECORD,
                occurred_at=self.clock.now(),
                attempts=retried.attempts,
                outcome=outcome,
                record_id=record_id,
                content_hash=stored.content_hash,
                storage_path=stored.relative_path,
            )
            increments: dict[str, object] = {
                "updated_at": self.clock.now(),
            }
            if outcome is ManifestOutcome.CREATED:
                increments["created_count"] = manifest.created_count + 1
            else:
                increments["existing_count"] = manifest.existing_count + 1
            manifest = _append_entry(manifest, entry, **increments)
            self.manifest_store.save(manifest)
            checkpoint = _replace_checkpoint(
                checkpoint,
                next_record_index=index + 1,
                updated_at=self.clock.now(),
            )
            self.checkpoint_store.save(checkpoint)
        return manifest, checkpoint

    def _quarantine(
        self,
        manifest: RunManifest,
        checkpoint: RunCheckpoint,
        *,
        request_id: str,
        record_id: str,
        attempts: int,
        failure: FailureDetail,
    ) -> tuple[RunManifest, RunCheckpoint]:
        """Durably record a terminal failure before advancing replay state."""
        occurred_at = self.clock.now()
        record = QuarantineRecord(
            run_id=manifest.configuration.run_id,
            request_id=request_id,
            record_id=record_id,
            occurred_at=occurred_at,
            attempts=attempts,
            failure=failure,
        )
        path = self.quarantine_store.store(record)
        entry = ManifestEntry(
            request_id=request_id,
            kind=RequestKind.RECORD,
            occurred_at=occurred_at,
            attempts=attempts,
            outcome=ManifestOutcome.QUARANTINED,
            record_id=record_id,
            quarantine_path=path,
            failure=failure,
        )
        manifest = _append_entry(
            manifest,
            entry,
            quarantined_count=manifest.quarantined_count + 1,
            updated_at=self.clock.now(),
        )
        self.manifest_store.save(manifest)
        checkpoint = _replace_checkpoint(
            checkpoint,
            next_record_index=checkpoint.next_record_index + 1,
            updated_at=self.clock.now(),
        )
        self.checkpoint_store.save(checkpoint)
        return manifest, checkpoint


def _entry_by_request_id(
    manifest: RunManifest,
    request_id: str,
) -> ManifestEntry | None:
    """Resolve one stable request identity from immutable manifest history."""
    return next(
        (entry for entry in manifest.entries if entry.request_id == request_id),
        None,
    )


def _replace_manifest(manifest: RunManifest, **updates: object) -> RunManifest:
    """Create validated manifest state from trusted internal updates."""
    return RunManifest.model_validate({**manifest.model_dump(), **updates})


def _replace_checkpoint(
    checkpoint: RunCheckpoint,
    **updates: object,
) -> RunCheckpoint:
    """Create validated checkpoint state from trusted internal updates."""
    return RunCheckpoint.model_validate({**checkpoint.model_dump(), **updates})


def _append_entry(
    manifest: RunManifest,
    entry: ManifestEntry,
    **updates: object,
) -> RunManifest:
    """Append one unique terminal entry and apply derived count updates."""
    if _entry_by_request_id(manifest, entry.request_id) is not None:
        raise IngestionRunError("The manifest request ID already exists.")
    merged: dict[str, object] = {
        **updates,
        "entries": (*manifest.entries, entry),
    }
    return _replace_manifest(manifest, **merged)
