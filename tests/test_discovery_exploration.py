"""Tests for deterministic query-matrix exploration orchestration."""

from pathlib import Path

from lowlands_lens.discovery.contracts import (
    EuropeanaSearchResponsePayload,
    SearchRequestConfiguration,
)
from lowlands_lens.discovery.exploration import (
    request_from_query,
    run_query_matrix,
    summarize_search,
)
from lowlands_lens.discovery.query_matrix import load_discovery_query_matrix

MATRIX_PATH = (
    Path(__file__).parents[1] / "config" / "phase3" / "discovery_queries_v1.toml"
)


class DeterministicSearcher:
    """Return one safe response for every matrix request."""

    def __init__(self) -> None:
        self.requests: list[SearchRequestConfiguration] = []

    def search(
        self,
        request: SearchRequestConfiguration,
    ) -> EuropeanaSearchResponsePayload:
        self.requests.append(request)
        return EuropeanaSearchResponsePayload.model_validate(
            {
                "success": True,
                "itemsCount": 1,
                "totalResults": 10,
                "items": [{"id": f"/synthetic/{request.query_id}"}],
                "facets": [
                    {
                        "name": "TYPE",
                        "fields": [{"label": "IMAGE", "count": 7}],
                    }
                ],
            }
        )


def test_query_translation_preserves_matrix_bounds_and_refinements() -> None:
    matrix = load_discovery_query_matrix(MATRIX_PATH)
    query = matrix.queries[0]

    request = request_from_query(query)

    assert request.query_id == query.query_id
    assert request.query == query.query_text
    assert request.refinements == query.filters
    assert request.facets == query.facets
    assert request.rows == query.page_size
    assert request.sample_limit == query.sample_limit

    rights_query = next(
        item for item in matrix.queries if item.query_id == "rights-en-001"
    )
    rights_request = request_from_query(rights_query)
    assert rights_request.reusability == "open"
    assert "reusability=open" not in rights_request.refinements


def test_summary_keeps_facets_samples_and_visible_limitations() -> None:
    matrix = load_discovery_query_matrix(MATRIX_PATH)
    query = matrix.queries[0]
    response = DeterministicSearcher().search(request_from_query(query))

    summary = summarize_search(query, response)

    assert summary.total_results == 10
    assert summary.facets[0].facet_name == "TYPE"
    assert summary.facets[0].values[0].count == 7
    assert summary.sampled_records[0].query_id == query.query_id
    assert len(summary.limitations) == 2


def test_matrix_executor_is_sequential_and_complete() -> None:
    matrix = load_discovery_query_matrix(MATRIX_PATH)
    searcher = DeterministicSearcher()

    summaries = run_query_matrix(searcher, matrix)

    assert len(summaries) == len(matrix.queries) == 13
    assert [request.query_id for request in searcher.requests] == [
        query.query_id for query in matrix.queries
    ]
