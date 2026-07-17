from dataclasses import replace
from pathlib import Path

import pytest

from lowlands_lens.discovery.query_matrix import (
    DiscoveryCategory,
    DiscoveryQueryMatrix,
    load_discovery_query_matrix,
)
from lowlands_lens.domain import Language

MATRIX_PATH = (
    Path(__file__).parents[1] / "config" / "phase3" / "discovery_queries_v1.toml"
)


def test_versioned_matrix_loads_with_required_coverage() -> None:
    matrix = load_discovery_query_matrix(MATRIX_PATH)

    assert matrix.schema_version == 1
    assert matrix.purpose == "phase_3_exploration_only"
    assert len(matrix.queries) == 13
    assert {query.language for query in matrix.queries} == set(Language)
    assert {query.category for query in matrix.queries} == set(DiscoveryCategory)

    query_ids = [query.query_id for query in matrix.queries]
    assert len(query_ids) == len(set(query_ids))


def test_matrix_rejects_duplicate_query_ids() -> None:
    matrix = load_discovery_query_matrix(MATRIX_PATH)
    duplicate = replace(
        matrix.queries[1],
        query_id=matrix.queries[0].query_id,
    )
    invalid_queries = (
        matrix.queries[0],
        duplicate,
        *matrix.queries[2:],
    )

    with pytest.raises(ValueError, match="Query IDs must be unique"):
        DiscoveryQueryMatrix(
            schema_version=matrix.schema_version,
            purpose=matrix.purpose,
            queries=invalid_queries,
        )


def test_query_rejects_an_unbounded_page_size() -> None:
    matrix = load_discovery_query_matrix(MATRIX_PATH)

    with pytest.raises(ValueError, match="page_size"):
        replace(matrix.queries[0], page_size=101)


def test_loader_rejects_a_missing_required_field(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid_matrix.toml"
    invalid_path.write_text(
        """
            schema_version = 1
            purpose = "phase_3_exploration_only"

            [[queries]]
            query_id = "invalid-en-001"
            category = "belgian_places"
            language = "en"
            purpose = "Demonstrate missing query text."
            expected_signal = "No valid result is expected."
            filters = []
            facets = ["TYPE"]
            page_size = 10
            sample_limit = 5
            hypothesis = "The loader should reject this entry."
            """.strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="query_text"):
        load_discovery_query_matrix(invalid_path)
