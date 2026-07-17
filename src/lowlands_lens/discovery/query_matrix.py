"""Versioned Phase 3 discovery query-matrix models and loading."""

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import cast

from lowlands_lens.domain import Language


class DiscoveryCategory(StrEnum):
    """Approved thematic categories for Phase 3 exploration."""

    BELGIAN_PLACES = "belgian_places"
    ARTISTS_AND_MOVEMENTS = "artists_and_movements"
    ARCHITECTURE_AND_URBAN_HISTORY = "architecture_and_urban_history"
    WAR_AND_PUBLIC_MEMORY = "war_and_public_memory"
    COLONIAL_AND_POSTCOLONIAL_HISTORY = "colonial_and_postcolonial_history"
    MIGRATION_AND_SOCIAL_CHANGE = "migration_and_social_change"
    DESIGN_POSTERS_AND_PHOTOGRAPHY = "design_posters_and_photography"
    FILM_AUDIO_TEXT_AND_OTHER_MEDIA = "film_audio_text_and_other_media"
    RIGHTS_AWARE_DISCOVERY = "rights_aware_discovery"
    CONTEMPORARY_CULTURE = "contemporary_culture"
    BROAD_AND_NOISY_SEARCHES = "broad_and_noisy_searches"


@dataclass(frozen=True, slots=True)
class DiscoveryQuery:
    """One bounded, reviewable Phase 3 exploration query."""

    query_id: str
    category: DiscoveryCategory
    language: Language
    query_text: str
    purpose: str
    expected_signal: str
    filters: tuple[str, ...]
    facets: tuple[str, ...]
    page_size: int
    sample_limit: int
    hypothesis: str

    def __post_init__(self) -> None:
        """Reject incomplete, duplicate, or unbounded query definitions."""
        required_text = {
            "query_id": self.query_id,
            "query_text": self.query_text,
            "purpose": self.purpose,
            "expected_signal": self.expected_signal,
            "hypothesis": self.hypothesis,
        }
        for field_name, value in required_text.items():
            if not value.strip():
                raise ValueError(f"{field_name} must be non-empty.")

        if len(self.query_text) > 500:
            raise ValueError("query_text cannot exceed 500 characters.")

        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be between 1 and 100.")

        if not 0 <= self.sample_limit <= self.page_size:
            raise ValueError("sample_limit must be between 0 and page_size.")

        if not self.facets:
            raise ValueError("At least one facet must be requested.")

        if len(set(self.filters)) != len(self.filters):
            raise ValueError("Filters must be unique.")

        if len(set(self.facets)) != len(self.facets):
            raise ValueError("Facets must be unique.")


@dataclass(frozen=True, slots=True)
class DiscoveryQueryMatrix:
    """Versioned collection of exploration-only discovery queries."""

    schema_version: int
    purpose: str
    queries: tuple[DiscoveryQuery, ...]

    def __post_init__(self) -> None:
        """Reject unsupported or empty discovery matrices."""
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1.")

        if self.purpose != "phase_3_exploration_only":
            raise ValueError("purpose must be phase_3_exploration_only.")

        if not self.queries:
            raise ValueError("The discovery matrix must contain queries.")

        query_ids = [query.query_id for query in self.queries]
        if len(query_ids) != len(set(query_ids)):
            raise ValueError("Query IDs must be unique.")

        required_languages = {
            Language.ENGLISH,
            Language.FRENCH,
            Language.DUTCH,
        }
        matrix_languages = {query.language for query in self.queries}
        if matrix_languages != required_languages:
            raise ValueError("The matrix must cover English, French, and Dutch.")

        matrix_categories = {query.category for query in self.queries}
        if matrix_categories != set(DiscoveryCategory):
            raise ValueError("The matrix must cover every discovery category.")


def _read_toml_document(path: Path) -> dict[str, object]:
    """Read one local TOML document."""
    with path.open("rb") as matrix_file:
        return tomllib.load(matrix_file)


def _require_string(table: dict[str, object], key: str) -> str:
    """Read one required, non-empty string."""
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value


def _require_integer(table: dict[str, object], key: str) -> int:
    """Read one required integer."""
    value = table.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer.")
    return value


def _require_string_tuple(
    table: dict[str, object],
    key: str,
) -> tuple[str, ...]:
    """Read a required TOML list containing only strings."""
    value = table.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings.")
    return tuple(cast(list[str], value))


def _parse_query(value: object) -> DiscoveryQuery:
    """Convert one untrusted TOML entry into a validated query."""
    if not isinstance(value, dict):
        raise ValueError("Each queries entry must be a TOML table.")

    table = cast(dict[str, object], value)
    return DiscoveryQuery(
        query_id=_require_string(table, "query_id"),
        category=DiscoveryCategory(_require_string(table, "category")),
        language=Language(_require_string(table, "language")),
        query_text=_require_string(table, "query_text"),
        purpose=_require_string(table, "purpose"),
        expected_signal=_require_string(table, "expected_signal"),
        filters=_require_string_tuple(table, "filters"),
        facets=_require_string_tuple(table, "facets"),
        page_size=_require_integer(table, "page_size"),
        sample_limit=_require_integer(table, "sample_limit"),
        hypothesis=_require_string(table, "hypothesis"),
    )


def load_discovery_query_matrix(path: Path) -> DiscoveryQueryMatrix:
    """Load and validate one versioned discovery-query matrix."""
    document = _read_toml_document(path)
    raw_queries = document.get("queries")
    if not isinstance(raw_queries, list):
        raise ValueError("queries must be a list of TOML tables.")

    return DiscoveryQueryMatrix(
        schema_version=_require_integer(document, "schema_version"),
        purpose=_require_string(document, "purpose"),
        queries=tuple(_parse_query(query) for query in raw_queries),
    )
