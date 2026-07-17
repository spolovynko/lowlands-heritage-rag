"""Validation tests for durable Phase 4 contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lowlands_lens.ingestion.contracts import (
    FailureCategory,
    FailureDetail,
    ManifestEntry,
    ManifestOutcome,
    RequestKind,
    RunCheckpoint,
    RunConfiguration,
    RunManifest,
    RunStatus,
)

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


def configuration(**updates: object) -> RunConfiguration:
    """Return one approved bounded test configuration."""
    values: dict[str, object] = {
        "run_id": "run-001",
        "query_id": "war-nl-001",
        "candidate_limit": 10,
        "record_request_limit": 5,
        "search_page_limit": 3,
        "output_root": "data/phase4",
    }
    values.update(updates)
    return RunConfiguration.model_validate(values)


def test_configuration_enforces_approved_scope() -> None:
    assert configuration().live_requests is False
    assert configuration().no_media is True

    with pytest.raises(ValidationError):
        configuration(query_id="noisy-en-001")
    with pytest.raises(ValidationError):
        configuration(candidate_limit=11)
    with pytest.raises(ValidationError):
        configuration(record_request_limit=6)
    with pytest.raises(ValidationError):
        configuration(live_requests=True)
    with pytest.raises(ValidationError):
        configuration(no_media=False)


def test_manifest_entries_reject_impossible_outcome_combinations() -> None:
    with pytest.raises(ValidationError, match="Search entries must capture"):
        ManifestEntry(
            request_id="search-page-0001",
            kind=RequestKind.SEARCH,
            occurred_at=NOW,
            attempts=1,
            outcome=ManifestOutcome.CREATED,
            cursor="*",
        )

    with pytest.raises(ValidationError, match="require hash and path"):
        ManifestEntry(
            request_id="record-0001",
            kind=RequestKind.RECORD,
            occurred_at=NOW,
            attempts=1,
            outcome=ManifestOutcome.CREATED,
            record_id="/dataset/record-1",
        )

    with pytest.raises(ValidationError, match="failure and path"):
        ManifestEntry(
            request_id="record-0001",
            kind=RequestKind.RECORD,
            occurred_at=NOW,
            attempts=1,
            outcome=ManifestOutcome.QUARANTINED,
            record_id="/dataset/record-1",
            failure=FailureDetail(
                category=FailureCategory.NOT_FOUND,
                retryable=False,
                message="The record was not found.",
            ),
        )


def test_manifest_and_checkpoint_reject_inconsistent_durable_state() -> None:
    config = configuration(candidate_limit=1, record_request_limit=1)
    with pytest.raises(ValidationError, match="finished_at"):
        RunManifest(
            configuration=config,
            status=RunStatus.COMPLETED,
            started_at=NOW,
            updated_at=NOW,
        )

    with pytest.raises(ValidationError, match="candidate IDs must be unique"):
        RunCheckpoint(
            run_id=config.run_id,
            candidate_record_ids=("/dataset/one", "/dataset/one"),
            updated_at=NOW,
        )

    with pytest.raises(ValidationError, match="cannot have next_cursor"):
        RunCheckpoint(
            run_id=config.run_id,
            search_complete=True,
            next_cursor="cursor-2",
            updated_at=NOW,
        )


def test_failure_contract_keeps_retry_guidance_scoped() -> None:
    with pytest.raises(ValidationError, match="valid only for rate limiting"):
        FailureDetail(
            category=FailureCategory.AUTHENTICATION,
            retryable=False,
            message="Authentication failed.",
            retry_after_seconds=10,
        )
