import pytest
from pydantic import ValidationError

from lowlands_lens.discovery.contracts import (
    DiscoveryError,
    DiscoveryErrorCategory,
    EuropeanaErrorPayload,
    EuropeanaRecordResponsePayload,
    EuropeanaSearchResponsePayload,
    FacetDistribution,
    FacetValueCount,
    RecordRequestConfiguration,
    SampledRecordReference,
    SearchExplorationSummary,
    SearchRequestConfiguration,
)


def search_payload() -> dict[str, object]:
    """Return one sanitized representative Search API payload."""
    return {
        "success": True,
        "itemsCount": 1,
        "totalResults": 42,
        "requestNumber": 7,
        "statsDuration": 15,
        "items": [
            {
                "id": "/2024903/example-001",
                "title": ["Bruxelles, exposition de 1958"],
                "dcDescription": ["Affiche culturelle synthétique."],
                "dataProvider": ["Synthetic Belgian Archive"],
                "provider": ["Synthetic Europeana Aggregator"],
                "language": ["fr", "nl"],
                "country": ["belgium"],
                "type": "IMAGE",
                "rights": ["http://creativecommons.org/publicdomain/mark/1.0/"],
                "year": ["1958"],
                "edmIsShownAt": "https://example.invalid/record/001",
                "edmPreview": "https://example.invalid/preview/001.jpg",
                "unknownItemField": "ignored",
            }
        ],
        "facets": [
            {
                "name": "TYPE",
                "fields": [
                    {
                        "label": "IMAGE",
                        "count": 40,
                    },
                    {
                        "label": "TEXT",
                        "count": 2,
                    },
                ],
            }
        ],
        "apikey": "fake-provider-field-that-must-not-be-retained",
        "unknownTopLevelField": "ignored",
    }


def record_payload() -> dict[str, object]:
    """Return one sanitized multilingual Record API payload."""
    return {
        "success": True,
        "requestNumber": 8,
        "statsDuration": 20,
        "object": {
            "about": "/2024903/example-001",
            "proxies": [
                {
                    "about": "/proxy/provider/example-001",
                    "dcTitle": {
                        "fr": ["Affiche de Bruxelles"],
                        "nl": ["Affiche uit Brussel"],
                    },
                    "dcDescription": {
                        "en": ["Synthetic description for contract tests."]
                    },
                    "dcDate": {
                        "def": ["1958"],
                    },
                    "dcSubject": {
                        "fr": ["exposition"],
                        "nl": ["tentoonstelling"],
                    },
                    "dcCreator": {
                        "def": ["Synthetic Designer"],
                    },
                    "dctermsSpatial": {
                        "fr": ["Bruxelles"],
                        "nl": ["Brussel"],
                    },
                    "edmType": {
                        "def": ["IMAGE"],
                    },
                }
            ],
            "aggregations": [
                {
                    "about": "/aggregation/provider/example-001",
                    "edmDataProvider": {"def": ["Synthetic Belgian Archive"]},
                    "edmProvider": {"def": ["Synthetic Europeana Aggregator"]},
                    "edmRights": {
                        "def": ["http://creativecommons.org/publicdomain/mark/1.0/"]
                    },
                    "edmIsShownAt": "https://example.invalid/record/001",
                    "edmIsShownBy": "https://example.invalid/object/001.jpg",
                    "edmPreview": "https://example.invalid/preview/001.jpg",
                    "webResources": [
                        {
                            "about": "https://example.invalid/object/001.jpg",
                            "edmRights": {
                                "def": [
                                    "http://creativecommons.org/publicdomain/mark/1.0/"
                                ]
                            },
                        }
                    ],
                }
            ],
            "unknownRecordField": "ignored",
        },
    }


def test_search_request_configuration_preserves_bounds() -> None:
    request = SearchRequestConfiguration(
        query_id="places-fr-001",
        query="Bruxelles",
        refinements=("YEAR:[1900 TO 2026]",),
        facets=("TYPE", "LANGUAGE"),
        rows=12,
        sample_limit=6,
    )

    assert request.profile == "facets"
    assert request.start is None
    assert request.cursor is None
    assert request.rows == 12
    assert request.sample_limit == 6


def test_search_request_configuration_rejects_unsafe_pagination() -> None:
    with pytest.raises(
        ValidationError,
        match="start and cursor cannot be used together",
    ):
        SearchRequestConfiguration(
            query_id="places-en-001",
            query="Brussels",
            facets=("TYPE",),
            rows=12,
            sample_limit=6,
            start=1,
            cursor="*",
        )

    with pytest.raises(
        ValidationError,
        match="cannot pass result 1000",
    ):
        SearchRequestConfiguration(
            query_id="places-en-001",
            query="Brussels",
            facets=("TYPE",),
            rows=12,
            sample_limit=6,
            start=995,
        )

    with pytest.raises(
        ValidationError,
        match="sample_limit cannot exceed rows",
    ):
        SearchRequestConfiguration(
            query_id="places-en-001",
            query="Brussels",
            facets=("TYPE",),
            rows=5,
            sample_limit=6,
        )


def test_record_request_requires_dataset_and_local_identifier() -> None:
    request = RecordRequestConfiguration(record_id="/2024903/example-001")

    assert request.record_id == "/2024903/example-001"

    with pytest.raises(ValidationError):
        RecordRequestConfiguration(record_id="example-001")


def test_search_payload_parses_selected_fields_and_ignores_unknowns() -> None:
    response = EuropeanaSearchResponsePayload.model_validate(search_payload())

    assert response.success is True
    assert response.items_count == 1
    assert response.total_results == 42
    assert response.items[0].record_id == "/2024903/example-001"
    assert response.items[0].languages == ["fr", "nl"]
    assert response.facets[0].name == "TYPE"
    assert response.facets[0].fields[0].count == 40

    dumped = response.model_dump()
    assert "apikey" not in dumped
    assert "unknownTopLevelField" not in dumped


def test_search_payload_accepts_missing_optional_fields_and_empty_facets() -> None:
    response = EuropeanaSearchResponsePayload.model_validate(
        {
            "success": True,
            "itemsCount": 0,
            "totalResults": 0,
            "items": [],
            "facets": [
                {
                    "name": "LANGUAGE",
                    "fields": [],
                }
            ],
        }
    )

    assert response.next_cursor is None
    assert response.items == []
    assert response.facets[0].fields == []
    assert response.request_number is None


def test_search_payload_rejects_malformed_required_fields() -> None:
    payload = search_payload()
    payload["totalResults"] = "forty-two"

    with pytest.raises(ValidationError, match="totalResults"):
        EuropeanaSearchResponsePayload.model_validate(payload)


def test_record_payload_preserves_multilingual_and_rights_values() -> None:
    response = EuropeanaRecordResponsePayload.model_validate(record_payload())

    record = response.record_object
    proxy = record.proxies[0]
    aggregation = record.aggregations[0]
    web_resource = aggregation.web_resources[0]

    assert proxy.titles["fr"] == ["Affiche de Bruxelles"]
    assert proxy.titles["nl"] == ["Affiche uit Brussel"]
    assert proxy.places["fr"] == ["Bruxelles"]
    assert proxy.places["nl"] == ["Brussel"]
    assert aggregation.providers["def"] == ["Synthetic Europeana Aggregator"]
    assert web_resource.rights["def"] == [
        "http://creativecommons.org/publicdomain/mark/1.0/"
    ]


def test_error_contracts_preserve_stable_failure_categories() -> None:
    provider_error = EuropeanaErrorPayload.model_validate(
        {
            "success": False,
            "message": "Request limit reached.",
            "providerDiagnostic": "ignored",
        }
    )
    discovery_error = DiscoveryError(
        category=DiscoveryErrorCategory.RATE_LIMITED,
        message="Europeana temporarily limited this bounded request.",
        status_code=429,
        retry_after_seconds=30,
    )

    assert provider_error.message == "Request limit reached."
    assert discovery_error.category is DiscoveryErrorCategory.RATE_LIMITED

    with pytest.raises(
        ValidationError,
        match="valid only for rate limiting",
    ):
        DiscoveryError(
            category=DiscoveryErrorCategory.AUTHENTICATION,
            message="Authentication failed.",
            status_code=401,
            retry_after_seconds=30,
        )


def test_summary_supports_empty_facets_and_traceable_samples() -> None:
    summary = SearchExplorationSummary(
        query_id="places-fr-001",
        total_results=42,
        items_count=1,
        facets=(
            FacetDistribution(
                facet_name="LANGUAGE",
                values=(),
            ),
            FacetDistribution(
                facet_name="TYPE",
                values=(
                    FacetValueCount(label="IMAGE", count=40),
                    FacetValueCount(label="TEXT", count=2),
                ),
            ),
        ),
        sampled_records=(
            SampledRecordReference(
                query_id="places-fr-001",
                record_id="/2024903/example-001",
                rank=1,
                sampling_reason="Inspect multilingual place metadata.",
            ),
        ),
        limitations=("Facet counts are a dated API snapshot.",),
    )

    assert summary.facets[0].values == ()
    assert summary.sampled_records[0].rank == 1


def test_summary_rejects_inconsistent_counts_and_query_references() -> None:
    with pytest.raises(
        ValidationError,
        match="items_count cannot exceed total_results",
    ):
        SearchExplorationSummary(
            query_id="places-en-001",
            total_results=0,
            items_count=1,
        )

    with pytest.raises(
        ValidationError,
        match="must reference the summary query ID",
    ):
        SearchExplorationSummary(
            query_id="places-en-001",
            total_results=1,
            items_count=1,
            sampled_records=(
                SampledRecordReference(
                    query_id="places-fr-001",
                    record_id="/2024903/example-001",
                    rank=1,
                    sampling_reason="Deliberately inconsistent test input.",
                ),
            ),
        )
