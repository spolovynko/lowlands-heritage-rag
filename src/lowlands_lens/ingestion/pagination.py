"""Deterministic cursor pagination state transitions."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from lowlands_lens.discovery.contracts import (
    EuropeanaRecordId,
    EuropeanaSearchResponsePayload,
    SearchRequestConfiguration,
)
from lowlands_lens.ingestion.contracts import RunCheckpoint


class PaginationTermination(StrEnum):
    """Reason candidate collection stopped after a Search page."""

    CONTINUE = "continue"
    NO_NEXT_CURSOR = "no_next_cursor"
    REPEATED_CURSOR = "repeated_cursor"
    CANDIDATE_LIMIT = "candidate_limit"
    PAGE_LIMIT = "page_limit"


class PaginationAdvance(BaseModel):
    """Immutable result of applying one provider page to a checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint: RunCheckpoint
    request_cursor: str
    new_candidate_ids: tuple[EuropeanaRecordId, ...]
    termination: PaginationTermination


def build_cursor_request(
    base_request: SearchRequestConfiguration,
    checkpoint: RunCheckpoint,
    candidate_limit: int,
) -> SearchRequestConfiguration:
    """Create the next bounded Search request from durable cursor state."""
    if checkpoint.search_complete or checkpoint.next_cursor is None:
        raise ValueError("Cannot build a Search request after pagination completes.")
    remaining = candidate_limit - len(checkpoint.candidate_record_ids)
    if remaining <= 0:
        raise ValueError("The candidate limit is already satisfied.")
    rows = min(base_request.rows, remaining)
    return SearchRequestConfiguration.model_validate(
        {
            **base_request.model_dump(),
            "rows": rows,
            "sample_limit": min(base_request.sample_limit, rows),
            "start": None,
            "cursor": checkpoint.next_cursor,
        }
    )


def advance_cursor(
    checkpoint: RunCheckpoint,
    response: EuropeanaSearchResponsePayload,
    *,
    candidate_limit: int,
    completed_page_count: int,
    page_limit: int,
    updated_at: datetime,
) -> PaginationAdvance:
    """Deduplicate one page and calculate the next durable cursor state."""
    if checkpoint.search_complete or checkpoint.next_cursor is None:
        raise ValueError("Cannot advance completed pagination.")
    if completed_page_count < 1:
        raise ValueError("completed_page_count must include the current page.")

    request_cursor = checkpoint.next_cursor
    known_ids = set(checkpoint.candidate_record_ids)
    all_ids = list(checkpoint.candidate_record_ids)
    new_ids: list[str] = []
    for item in response.items:
        if item.record_id in known_ids:
            continue
        known_ids.add(item.record_id)
        all_ids.append(item.record_id)
        new_ids.append(item.record_id)
        if len(all_ids) == candidate_limit:
            break

    seen_cursors = (*checkpoint.seen_cursors, request_cursor)
    next_cursor = response.next_cursor
    if len(all_ids) >= candidate_limit:
        termination = PaginationTermination.CANDIDATE_LIMIT
    elif completed_page_count >= page_limit:
        termination = PaginationTermination.PAGE_LIMIT
    elif next_cursor is None:
        termination = PaginationTermination.NO_NEXT_CURSOR
    elif next_cursor in seen_cursors:
        termination = PaginationTermination.REPEATED_CURSOR
    else:
        termination = PaginationTermination.CONTINUE

    search_complete = termination is not PaginationTermination.CONTINUE
    advanced = RunCheckpoint.model_validate(
        {
            **checkpoint.model_dump(),
            "candidate_record_ids": tuple(all_ids),
            "seen_cursors": seen_cursors,
            "next_cursor": None if search_complete else next_cursor,
            "search_complete": search_complete,
            "updated_at": updated_at,
        }
    )
    return PaginationAdvance(
        checkpoint=advanced,
        request_cursor=request_cursor,
        new_candidate_ids=tuple(new_ids),
        termination=termination,
    )
