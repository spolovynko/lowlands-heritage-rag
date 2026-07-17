"""Deterministic in-memory adapter for the Phase 2 search journey."""

import re
from collections.abc import Sequence
from typing import Final

from lowlands_lens.adapters.synthetic_records import SyntheticFixture
from lowlands_lens.application.retrieval import (
    RetrievalQuery,
    RetrievalResult,
    RetrievalUnavailableError,
)
from lowlands_lens.domain import EvidenceRecord

SIMULATED_FAILURE_QUERY: Final = "simulate-search-error"
MOCK_LIMITATION: Final = (
    "Results come from deterministic synthetic fixtures, not Europeana or a "
    "production retrieval system."
)


class InMemoryRetrievalAdapter:
    """Search and resolve a fixed set of synthetic records."""

    def __init__(self, fixtures: Sequence[SyntheticFixture]) -> None:
        self._fixtures = tuple(fixtures)
        self._records_by_id = {
            fixture.evidence.evidence_id: fixture.evidence for fixture in fixtures
        }

    def search(self, query: RetrievalQuery) -> RetrievalResult:
        """Return deterministic token matches in fixture order."""
        normalized_query = query.text.strip().casefold()
        if normalized_query == SIMULATED_FAILURE_QUERY:
            raise RetrievalUnavailableError(
                "The synthetic retrieval failure was requested."
            )

        query_terms = self._terms(normalized_query)
        matches = tuple(
            fixture.evidence
            for fixture in self._fixtures
            if query_terms.intersection(self._fixture_terms(fixture))
        )
        return RetrievalResult(
            records=matches[: query.limit],
            total=len(matches),
            limitations=(MOCK_LIMITATION,),
        )

    def get_by_ids(self, evidence_ids: Sequence[str]) -> tuple[EvidenceRecord, ...]:
        """Resolve known identifiers while preserving request order."""
        return tuple(
            self._records_by_id[evidence_id]
            for evidence_id in evidence_ids
            if evidence_id in self._records_by_id
        )

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {term for term in re.findall(r"[\w-]+", value) if len(term) > 1}

    def _fixture_terms(self, fixture: SyntheticFixture) -> set[str]:
        values = [*fixture.search_terms]
        values.extend(title.text for title in fixture.evidence.titles)
        values.extend(description.text for description in fixture.evidence.descriptions)
        return self._terms(" ".join(values).casefold())
