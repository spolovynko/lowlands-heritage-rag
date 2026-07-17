import pytest

from lowlands_lens.adapters.in_memory_retrieval import (
    InMemoryRetrievalAdapter,
)
from lowlands_lens.adapters.synthetic_records import SYNTHETIC_FIXTURES
from lowlands_lens.application.retrieval import (
    RetrievalQuery,
    RetrievalUnavailableError,
)
from lowlands_lens.domain import Language


@pytest.fixture
def retrieval() -> InMemoryRetrievalAdapter:
    return InMemoryRetrievalAdapter(SYNTHETIC_FIXTURES)


def test_search_returns_deterministic_synthetic_matches(
    retrieval: InMemoryRetrievalAdapter,
) -> None:
    result = retrieval.search(
        RetrievalQuery(text="poster", language=Language.ENGLISH, limit=10)
    )

    assert result.total == 1
    assert [record.evidence_id for record in result.records] == ["synthetic-poster-001"]
    assert all(record.is_synthetic for record in result.records)
    assert "not Europeana" in result.limitations[0]


def test_search_reports_total_before_applying_limit(
    retrieval: InMemoryRetrievalAdapter,
) -> None:
    result = retrieval.search(
        RetrievalQuery(
            text="photograph audio",
            language=Language.ENGLISH,
            limit=1,
        )
    )

    assert result.total == 2
    assert len(result.records) == 1


def test_search_can_return_a_valid_empty_result(
    retrieval: InMemoryRetrievalAdapter,
) -> None:
    result = retrieval.search(
        RetrievalQuery(
            text="no matching object",
            language=Language.ENGLISH,
            limit=10,
        )
    )

    assert result.total == 0
    assert result.records == ()


def test_search_failure_is_distinct_from_empty(
    retrieval: InMemoryRetrievalAdapter,
) -> None:
    with pytest.raises(RetrievalUnavailableError):
        retrieval.search(
            RetrievalQuery(
                text="simulate-search-error",
                language=Language.ENGLISH,
                limit=10,
            )
        )


def test_repository_preserves_requested_order_and_ignores_unknown_ids(
    retrieval: InMemoryRetrievalAdapter,
) -> None:
    records = retrieval.get_by_ids(
        [
            "synthetic-audio-003",
            "unknown-record",
            "synthetic-poster-001",
        ]
    )

    assert [record.evidence_id for record in records] == [
        "synthetic-audio-003",
        "synthetic-poster-001",
    ]
