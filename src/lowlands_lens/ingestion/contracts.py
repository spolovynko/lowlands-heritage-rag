"""Validated contracts for reliable Bronze ingestion."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lowlands_lens.discovery.contracts import EuropeanaRecordId

NonEmptyText = Annotated[str, Field(min_length=1)]
SafeIdentifier = Annotated[
    str,
    Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"),
]
ContentHash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class IngestionContractModel(BaseModel):
    """Strict immutable base for project-controlled ingestion state."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class RunStatus(StrEnum):
    """Lifecycle state of one bounded ingestion run."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class RequestKind(StrEnum):
    """Provider request represented by a manifest entry."""

    SEARCH = "search"
    RECORD = "record"


class ManifestOutcome(StrEnum):
    """Durable outcome of one logical ingestion request."""

    PAGE_CAPTURED = "page_captured"
    CREATED = "created"
    ALREADY_PRESENT = "already_present"
    QUARANTINED = "quarantined"


class StorageOutcome(StrEnum):
    """Result of storing one immutable Bronze version."""

    CREATED = "created"
    ALREADY_PRESENT = "already_present"


class FailureCategory(StrEnum):
    """Stable sanitized failure classifications."""

    TIMEOUT = "timeout"
    TRANSPORT = "transport"
    RATE_LIMITED = "rate_limited"
    PROVIDER_SERVER = "provider_server"
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not_found"
    INVALID_JSON = "invalid_json"
    INVALID_RESPONSE = "invalid_response"
    INTEGRITY = "integrity"
    RETRY_EXHAUSTED = "retry_exhausted"
    REQUEST_BUDGET_EXHAUSTED = "request_budget_exhausted"
    UNKNOWN = "unknown"


class RunConfiguration(IngestionContractModel):
    """Approved immutable bounds and source selection for one run."""

    schema_version: Literal[1] = 1
    run_id: SafeIdentifier
    query_id: Literal["war-nl-001"]
    candidate_limit: int = Field(ge=1, le=10)
    record_request_limit: int = Field(ge=1, le=5)
    search_page_limit: int = Field(ge=1, le=10)
    output_root: NonEmptyText
    live_requests: Literal[False] = False
    no_media: Literal[True] = True
    recovery_of_run_id: SafeIdentifier | None = None
    selected_failure_request_ids: tuple[SafeIdentifier, ...] = ()

    @model_validator(mode="after")
    def validate_recovery_scope(self) -> Self:
        """Require explicit, unique failure selection for recovery runs."""
        has_source = self.recovery_of_run_id is not None
        has_failures = bool(self.selected_failure_request_ids)
        if has_source != has_failures:
            raise ValueError(
                "Recovery requires both source run and selected failure requests."
            )
        if len(self.selected_failure_request_ids) != len(
            set(self.selected_failure_request_ids)
        ):
            raise ValueError("Selected recovery request IDs must be unique.")
        if self.recovery_of_run_id == self.run_id:
            raise ValueError("A recovery run must have a new run ID.")
        return self


class FailureDetail(IngestionContractModel):
    """Sanitized provider or local failure information."""

    category: FailureCategory
    retryable: bool
    message: NonEmptyText
    status_code: int | None = Field(default=None, ge=100, le=599)
    retry_after_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_retry_guidance(self) -> Self:
        """Keep Retry-After guidance exclusive to rate limiting."""
        if (
            self.retry_after_seconds is not None
            and self.category is not FailureCategory.RATE_LIMITED
        ):
            raise ValueError("retry_after_seconds is valid only for rate limiting.")
        return self


class ManifestEntry(IngestionContractModel):
    """One durable, secret-safe request outcome."""

    request_id: SafeIdentifier
    kind: RequestKind
    occurred_at: datetime
    attempts: int = Field(ge=1)
    outcome: ManifestOutcome
    record_id: EuropeanaRecordId | None = None
    cursor: str | None = None
    next_cursor: str | None = None
    candidate_ids: tuple[EuropeanaRecordId, ...] = ()
    content_hash: ContentHash | None = None
    storage_path: NonEmptyText | None = None
    quarantine_path: NonEmptyText | None = None
    failure: FailureDetail | None = None

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> Self:
        """Reject combinations that cannot describe a real request outcome."""
        _require_aware(self.occurred_at, "occurred_at")
        if self.kind is RequestKind.SEARCH:
            if self.outcome is not ManifestOutcome.PAGE_CAPTURED:
                raise ValueError("Search entries must capture a page.")
            if self.cursor is None:
                raise ValueError("Search entries require the request cursor.")
            if self.record_id is not None or self.content_hash is not None:
                raise ValueError("Search entries cannot identify a raw Record object.")
            if (
                self.storage_path is not None
                or self.quarantine_path is not None
                or self.failure is not None
            ):
                raise ValueError(
                    "Successful Search entries cannot store object outcomes."
                )
            return self

        if self.record_id is None:
            raise ValueError("Record entries require record_id.")
        if (
            self.candidate_ids
            or self.cursor is not None
            or self.next_cursor is not None
        ):
            raise ValueError("Record entries cannot contain Search page state.")

        if self.outcome in {
            ManifestOutcome.CREATED,
            ManifestOutcome.ALREADY_PRESENT,
        }:
            if self.content_hash is None or self.storage_path is None:
                raise ValueError("Stored Record outcomes require hash and path.")
            if self.failure is not None or self.quarantine_path is not None:
                raise ValueError("Stored Record outcomes cannot contain a failure.")
        elif self.outcome is ManifestOutcome.QUARANTINED:
            if self.failure is None or self.quarantine_path is None:
                raise ValueError("Quarantined outcomes require failure and path.")
            if self.content_hash is not None or self.storage_path is not None:
                raise ValueError("Quarantined outcomes cannot reference a raw object.")
        else:
            raise ValueError("Record entries require a Record outcome.")
        return self


class RunManifest(IngestionContractModel):
    """Complete durable state and provenance for one ingestion run."""

    configuration: RunConfiguration
    status: RunStatus
    started_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    candidate_count: int = Field(default=0, ge=0)
    search_request_count: int = Field(default=0, ge=0)
    record_request_count: int = Field(default=0, ge=0)
    created_count: int = Field(default=0, ge=0)
    existing_count: int = Field(default=0, ge=0)
    quarantined_count: int = Field(default=0, ge=0)
    entries: tuple[ManifestEntry, ...] = ()

    @model_validator(mode="after")
    def validate_manifest_state(self) -> Self:
        """Require consistent timestamps, counts, and request identities."""
        _require_aware(self.started_at, "started_at")
        _require_aware(self.updated_at, "updated_at")
        if self.finished_at is not None:
            _require_aware(self.finished_at, "finished_at")
        terminal = self.status in {
            RunStatus.COMPLETED,
            RunStatus.INTERRUPTED,
            RunStatus.FAILED,
        }
        if terminal != (self.finished_at is not None):
            raise ValueError("Terminal run states require finished_at exclusively.")
        request_ids = [entry.request_id for entry in self.entries]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("Manifest request IDs must be unique.")
        if self.candidate_count > self.configuration.candidate_limit:
            raise ValueError("candidate_count exceeds the approved limit.")
        if self.record_request_count > self.configuration.record_request_limit:
            raise ValueError("record_request_count exceeds the approved limit.")
        if self.search_request_count > self.configuration.search_page_limit:
            raise ValueError("search_request_count exceeds the approved page limit.")
        search_entries = sum(entry.kind is RequestKind.SEARCH for entry in self.entries)
        record_entries = sum(entry.kind is RequestKind.RECORD for entry in self.entries)
        if search_entries > self.search_request_count:
            raise ValueError("Search entries exceed reserved Search requests.")
        if record_entries > self.record_request_count:
            raise ValueError("Record entries exceed reserved Record requests.")
        if self.created_count != sum(
            entry.outcome is ManifestOutcome.CREATED for entry in self.entries
        ):
            raise ValueError("created_count disagrees with manifest entries.")
        if self.existing_count != sum(
            entry.outcome is ManifestOutcome.ALREADY_PRESENT for entry in self.entries
        ):
            raise ValueError("existing_count disagrees with manifest entries.")
        if self.quarantined_count != sum(
            entry.outcome is ManifestOutcome.QUARANTINED for entry in self.entries
        ):
            raise ValueError("quarantined_count disagrees with manifest entries.")
        return self


class RunCheckpoint(IngestionContractModel):
    """Last durable cursor and Record-processing position for one run."""

    schema_version: Literal[1] = 1
    run_id: SafeIdentifier
    candidate_record_ids: tuple[EuropeanaRecordId, ...] = ()
    seen_cursors: tuple[NonEmptyText, ...] = ()
    next_cursor: NonEmptyText | None = "*"
    search_complete: bool = False
    next_record_index: int = Field(default=0, ge=0)
    updated_at: datetime

    @model_validator(mode="after")
    def validate_checkpoint(self) -> Self:
        """Reject duplicate state and impossible replay positions."""
        _require_aware(self.updated_at, "updated_at")
        if len(self.candidate_record_ids) != len(set(self.candidate_record_ids)):
            raise ValueError("Checkpoint candidate IDs must be unique.")
        if len(self.seen_cursors) != len(set(self.seen_cursors)):
            raise ValueError("Checkpoint cursors must be unique.")
        if self.next_record_index > len(self.candidate_record_ids):
            raise ValueError("next_record_index exceeds collected candidates.")
        if self.search_complete and self.next_cursor is not None:
            raise ValueError("Completed Search checkpoints cannot have next_cursor.")
        if not self.search_complete and self.next_cursor is None:
            raise ValueError("Incomplete Search checkpoints require next_cursor.")
        return self


class StoredBronzeObject(IngestionContractModel):
    """Immutable result returned by the Bronze object store."""

    record_id: EuropeanaRecordId
    content_hash: ContentHash
    relative_path: NonEmptyText
    outcome: StorageOutcome
    stored_size_bytes: int = Field(ge=1)


class QuarantineRecord(IngestionContractModel):
    """Sanitized durable terminal failure for explicit recovery."""

    schema_version: Literal[1] = 1
    run_id: SafeIdentifier
    request_id: SafeIdentifier
    record_id: EuropeanaRecordId
    occurred_at: datetime
    attempts: int = Field(ge=1)
    failure: FailureDetail

    @model_validator(mode="after")
    def validate_timestamp(self) -> Self:
        """Require an unambiguous failure timestamp."""
        _require_aware(self.occurred_at, "occurred_at")
        return self


class RetryPolicy(IngestionContractModel):
    """Bounded retry attempts and waiting budget."""

    max_attempts: int = Field(default=3, ge=1, le=5)
    max_total_delay_seconds: float = Field(default=30.0, ge=0.0, le=120.0)
    base_delay_seconds: float = Field(default=1.0, ge=0.0, le=30.0)
    max_delay_seconds: float = Field(default=10.0, ge=0.0, le=60.0)
    jitter_ratio: float = Field(default=0.2, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_delay_range(self) -> Self:
        """Keep the exponential delay bounded by its declared maximum."""
        if self.base_delay_seconds > self.max_delay_seconds:
            raise ValueError("base_delay_seconds cannot exceed max_delay_seconds.")
        return self


def _require_aware(value: datetime, field_name: str) -> None:
    """Reject local or ambiguous datetimes in durable contracts."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
