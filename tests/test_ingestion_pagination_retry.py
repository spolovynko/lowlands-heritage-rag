"""Deterministic pagination and retry-policy tests."""

from datetime import UTC, datetime

import pytest

from lowlands_lens.discovery.client import (
    EuropeanaAuthenticationError,
    EuropeanaHttpStatusError,
    EuropeanaRateLimitError,
    EuropeanaTimeoutError,
)
from lowlands_lens.discovery.contracts import (
    EuropeanaSearchResponsePayload,
    SearchRequestConfiguration,
)
from lowlands_lens.ingestion.contracts import (
    FailureCategory,
    RetryPolicy,
    RunCheckpoint,
)
from lowlands_lens.ingestion.pagination import (
    PaginationTermination,
    advance_cursor,
    build_cursor_request,
)
from lowlands_lens.ingestion.retry import OperationFailedError, execute_with_retry

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


class RecordingSleeper:
    """Record retry delays without waiting."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


class FixedJitter:
    """Return one deterministic jitter fraction."""

    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def fraction(self) -> float:
        return self.value


def response(ids: list[str], next_cursor: str | None) -> EuropeanaSearchResponsePayload:
    """Build one safe synthetic Search page."""
    return EuropeanaSearchResponsePayload.model_validate(
        {
            "success": True,
            "itemsCount": len(ids),
            "totalResults": 100,
            "nextCursor": next_cursor,
            "items": [{"id": record_id} for record_id in ids],
        }
    )


def base_request() -> SearchRequestConfiguration:
    """Return one approved cursor-free Search request."""
    return SearchRequestConfiguration(
        query_id="war-nl-001",
        query="België Eerste Wereldoorlog herdenking",
        facets=("TYPE",),
        rows=3,
        sample_limit=2,
    )


def test_pagination_deduplicates_ids_and_stops_on_repeated_cursor() -> None:
    checkpoint = RunCheckpoint(run_id="run-001", updated_at=NOW)
    request = build_cursor_request(base_request(), checkpoint, candidate_limit=4)
    assert request.cursor == "*"

    first = advance_cursor(
        checkpoint,
        response(["/dataset/one", "/dataset/two"], "cursor-2"),
        candidate_limit=4,
        completed_page_count=1,
        page_limit=4,
        updated_at=NOW,
    )
    second = advance_cursor(
        first.checkpoint,
        response(["/dataset/two", "/dataset/three"], "cursor-2"),
        candidate_limit=4,
        completed_page_count=2,
        page_limit=4,
        updated_at=NOW,
    )

    assert first.termination is PaginationTermination.CONTINUE
    assert second.termination is PaginationTermination.REPEATED_CURSOR
    assert second.new_candidate_ids == ("/dataset/three",)
    assert second.checkpoint.candidate_record_ids == (
        "/dataset/one",
        "/dataset/two",
        "/dataset/three",
    )
    assert second.checkpoint.search_complete is True


@pytest.mark.parametrize(
    ("ids", "next_cursor", "page_count", "candidate_limit", "page_limit", "reason"),
    [
        ([], None, 1, 5, 5, PaginationTermination.NO_NEXT_CURSOR),
        (["/dataset/one"], "next", 1, 1, 5, PaginationTermination.CANDIDATE_LIMIT),
        (["/dataset/one"], "next", 1, 5, 1, PaginationTermination.PAGE_LIMIT),
    ],
)
def test_pagination_has_bounded_termination_rules(
    ids: list[str],
    next_cursor: str | None,
    page_count: int,
    candidate_limit: int,
    page_limit: int,
    reason: PaginationTermination,
) -> None:
    advance = advance_cursor(
        RunCheckpoint(run_id="run-001", updated_at=NOW),
        response(ids, next_cursor),
        candidate_limit=candidate_limit,
        completed_page_count=page_count,
        page_limit=page_limit,
        updated_at=NOW,
    )
    assert advance.termination is reason
    assert advance.checkpoint.search_complete is True


def test_retry_uses_retry_after_and_exponential_delay_without_waiting() -> None:
    calls = 0
    reservations = 0
    sleeper = RecordingSleeper()

    def reserve() -> None:
        nonlocal reservations
        reservations += 1

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise EuropeanaRateLimitError(4)
        if calls == 2:
            raise EuropeanaTimeoutError("sanitized")
        return "ok"

    result = execute_with_retry(
        operation,
        policy=RetryPolicy(max_attempts=3, jitter_ratio=0.0),
        sleeper=sleeper,
        jitter=FixedJitter(),
        before_attempt=reserve,
    )

    assert result.value == "ok"
    assert result.attempts == 3
    assert reservations == 3
    assert sleeper.delays == [4.0, 2.0]


@pytest.mark.parametrize(
    ("error", "category", "attempts"),
    [
        (EuropeanaAuthenticationError("safe"), FailureCategory.AUTHENTICATION, 1),
        (EuropeanaHttpStatusError(503), FailureCategory.RETRY_EXHAUSTED, 2),
    ],
)
def test_retry_stops_for_permanent_or_exhausted_failures(
    error: Exception,
    category: FailureCategory,
    attempts: int,
) -> None:
    sleeper = RecordingSleeper()

    def operation() -> str:
        raise error

    with pytest.raises(OperationFailedError) as captured:
        execute_with_retry(
            operation,
            policy=RetryPolicy(max_attempts=2, jitter_ratio=0.0),
            sleeper=sleeper,
            jitter=FixedJitter(),
            before_attempt=lambda: None,
        )

    assert captured.value.failure.category is category
    assert captured.value.attempts == attempts
    assert "safe" not in str(captured.value)
