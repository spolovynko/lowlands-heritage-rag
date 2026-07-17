"""Integrity tests for the tracked Phase 3 aggregate observations."""

import tomllib
from pathlib import Path
from typing import cast

from lowlands_lens.discovery.query_matrix import load_discovery_query_matrix

ROOT = Path(__file__).parents[1]
MATRIX_PATH = ROOT / "config" / "phase3" / "discovery_queries_v1.toml"
OBSERVATIONS_PATH = (
    ROOT / "config" / "phase3" / "discovery_observations_2026-07-17.toml"
)


def load_observations() -> dict[str, object]:
    """Load the tracked aggregate observation document."""
    with OBSERVATIONS_PATH.open("rb") as stream:
        return tomllib.load(stream)


def test_observations_match_the_versioned_query_matrix() -> None:
    matrix = load_discovery_query_matrix(MATRIX_PATH)
    observations = load_observations()
    query_results = cast(list[dict[str, object]], observations["query_results"])

    assert observations["schema_version"] == 1
    assert observations["matrix_schema_version"] == matrix.schema_version
    assert observations["query_count"] == len(matrix.queries)
    assert [result["query_id"] for result in query_results] == [
        query.query_id for query in matrix.queries
    ]
    assert all(cast(int, result["total_results"]) >= 0 for result in query_results)


def test_observations_are_bounded_and_contain_no_secret_fields() -> None:
    observations = load_observations()
    serialized = OBSERVATIONS_PATH.read_text(encoding="utf-8").casefold()
    samples = cast(
        list[dict[str, object]],
        observations["belgian_connection_samples"],
    )

    assert observations["search_request_count"] == 13
    assert observations["record_sample_count"] == 6
    assert len(samples) == 6
    assert {sample["classification"] for sample in samples} == {
        "include",
        "manual_review",
    }
    assert "apikey" not in serialized
    assert "x-api-key" not in serialized
    assert "wskey" not in serialized
