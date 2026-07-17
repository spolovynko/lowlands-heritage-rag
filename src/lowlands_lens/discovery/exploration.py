"""Deterministic orchestration for bounded Phase 3 discovery searches."""

from typing import Literal, Protocol, cast

from lowlands_lens.discovery.contracts import (
    EuropeanaSearchResponsePayload,
    FacetDistribution,
    FacetValueCount,
    SampledRecordReference,
    SearchExplorationSummary,
    SearchRequestConfiguration,
)
from lowlands_lens.discovery.query_matrix import DiscoveryQuery, DiscoveryQueryMatrix


class DiscoverySearcher(Protocol):
    """Search capability required by the matrix executor."""

    def search(
        self,
        request: SearchRequestConfiguration,
    ) -> EuropeanaSearchResponsePayload:
        """Execute one bounded search."""
        ...


def request_from_query(query: DiscoveryQuery) -> SearchRequestConfiguration:
    """Translate one approved matrix entry into a client request."""
    dedicated_reusability = tuple(
        value.removeprefix("reusability=")
        for value in query.filters
        if value.startswith("reusability=")
    )
    if len(dedicated_reusability) > 1:
        raise ValueError("A query may define only one reusability filter.")
    reusability = (
        cast(
            Literal["open", "restricted", "permission"],
            dedicated_reusability[0],
        )
        if dedicated_reusability
        else None
    )
    refinements = tuple(
        value for value in query.filters if not value.startswith("reusability=")
    )
    return SearchRequestConfiguration(
        query_id=query.query_id,
        query=query.query_text,
        refinements=refinements,
        facets=query.facets,
        rows=query.page_size,
        sample_limit=query.sample_limit,
        reusability=reusability,
    )


def summarize_search(
    query: DiscoveryQuery,
    response: EuropeanaSearchResponsePayload,
) -> SearchExplorationSummary:
    """Convert one provider response into a project-controlled summary."""
    facets = tuple(
        FacetDistribution(
            facet_name=facet.name,
            values=tuple(
                FacetValueCount(label=value.label, count=value.count)
                for value in facet.fields
            ),
        )
        for facet in response.facets
    )
    sampled_records = tuple(
        SampledRecordReference(
            query_id=query.query_id,
            record_id=item.record_id,
            rank=rank,
            sampling_reason=(
                f"Bounded rank sample for {query.category.value} discovery."
            ),
        )
        for rank, item in enumerate(
            response.items[: query.sample_limit],
            start=1,
        )
    )
    return SearchExplorationSummary(
        query_id=query.query_id,
        total_results=response.total_results,
        items_count=response.items_count,
        facets=facets,
        sampled_records=sampled_records,
        limitations=(
            "Counts and facets are a dated Europeana API snapshot.",
            "Rank samples do not establish corpus relevance or representativeness.",
        ),
    )


def run_query_matrix(
    searcher: DiscoverySearcher,
    matrix: DiscoveryQueryMatrix,
) -> tuple[SearchExplorationSummary, ...]:
    """Run the approved matrix sequentially without retries or concurrency."""
    summaries: list[SearchExplorationSummary] = []
    for query in matrix.queries:
        response = searcher.search(request_from_query(query))
        summaries.append(summarize_search(query, response))
    return tuple(summaries)
