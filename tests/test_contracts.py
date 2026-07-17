import pytest
from pydantic import TypeAdapter, ValidationError

from lowlands_lens.api.contracts import (
    AbstainedResponse,
    AnsweredResponse,
    AnswerRequest,
    AnswerResponse,
    Citation,
    ErrorCode,
    ErrorResponse,
    Evidence,
    GenerationUnavailableResponse,
    LocalizedText,
    RightsStatement,
    SearchOutcome,
    SearchRequest,
    SearchResponse,
    SupportedLanguage,
)


def evidence_payload() -> dict[str, object]:
    """Return one complete deterministic synthetic evidence payload."""
    return {
        "evidence_id": "synthetic-object-001",
        "is_synthetic": True,
        "titles": [
            {
                "text": "Synthetic post-war exhibition poster",
                "language": "en",
            }
        ],
        "descriptions": [
            {
                "text": "A synthetic record created only for local development.",
                "language": "en",
            }
        ],
        "media_type": "image",
        "object_type": "poster",
        "date_display": "circa 1958",
        "providers": [
            {
                "provider_id": "synthetic-provider-001",
                "name": "Synthetic Heritage Lab",
                "role": "data_provider",
                "homepage_url": "https://example.invalid/provider",
            }
        ],
        "source_links": [
            {
                "kind": "record",
                "label": "Synthetic record page",
                "url": "https://example.invalid/record/001",
            }
        ],
        "rights": [
            {
                "scope": "metadata",
                "status": "known",
                "label": "CC0",
                "uri": "https://creativecommons.org/publicdomain/zero/1.0/",
            },
            {
                "scope": "digital_object",
                "status": "unknown",
                "label": "Rights information unavailable",
                "uri": None,
            },
        ],
    }


def citation_payload() -> dict[str, object]:
    """Return one deterministic citation payload."""
    return {
        "citation_id": "citation-001",
        "label": "[1] Synthetic post-war exhibition poster",
        "evidence_ids": ["synthetic-object-001"],
    }


def test_contracts_strip_whitespace_and_forbid_extra_fields() -> None:
    text = LocalizedText.model_validate(
        {
            "text": "  Synthetic title  ",
            "language": "en",
        }
    )

    assert text.text == "Synthetic title"
    assert text.language == "en"

    with pytest.raises(ValidationError):
        LocalizedText.model_validate(
            {
                "text": "Synthetic title",
                "language": "en",
                "unexpected": True,
            }
        )


def test_unknown_rights_cannot_include_uri() -> None:
    unknown = RightsStatement.model_validate(
        {
            "scope": "digital_object",
            "status": "unknown",
            "label": "Rights information unavailable",
            "uri": None,
        }
    )

    assert unknown.uri is None

    with pytest.raises(
        ValidationError,
        match="Unknown rights cannot include a rights URI",
    ):
        RightsStatement.model_validate(
            {
                "scope": "digital_object",
                "status": "unknown",
                "label": "Unknown",
                "uri": "https://example.invalid/rights",
            }
        )


def test_evidence_requires_both_rights_scopes() -> None:
    evidence = Evidence.model_validate(evidence_payload())

    assert evidence.evidence_id == "synthetic-object-001"
    assert evidence.is_synthetic is True
    assert len(evidence.rights) == 2

    invalid_payload = evidence_payload()
    invalid_payload["rights"] = [
        {
            "scope": "metadata",
            "status": "known",
            "label": "CC0",
        },
        {
            "scope": "metadata",
            "status": "known",
            "label": "CC0",
        },
    ]

    with pytest.raises(
        ValidationError,
        match="one metadata and one digital-object rights statement",
    ):
        Evidence.model_validate(invalid_payload)


def test_search_request_validates_language_query_and_limit() -> None:
    request = SearchRequest.model_validate(
        {
            "query": "  synthetic posters  ",
            "language": "fr",
        }
    )

    assert request.query == "synthetic posters"
    assert request.language is SupportedLanguage.FRENCH
    assert request.limit == 10

    with pytest.raises(ValidationError):
        SearchRequest.model_validate(
            {
                "query": "synthetic posters",
                "language": "de",
            }
        )

    with pytest.raises(ValidationError):
        SearchRequest.model_validate(
            {
                "query": "synthetic posters",
                "language": "en",
                "limit": 21,
            }
        )


def test_search_response_distinguishes_results_from_empty() -> None:
    evidence = Evidence.model_validate(evidence_payload())

    results = SearchResponse(
        outcome=SearchOutcome.RESULTS,
        query="synthetic posters",
        language=SupportedLanguage.ENGLISH,
        results=[evidence],
        total=1,
    )
    empty = SearchResponse(
        outcome=SearchOutcome.EMPTY,
        query="no matches",
        language=SupportedLanguage.ENGLISH,
        results=[],
        total=0,
    )

    assert results.results == [evidence]
    assert empty.results == []

    with pytest.raises(
        ValidationError,
        match="empty search must have a total of zero",
    ):
        SearchResponse(
            outcome=SearchOutcome.EMPTY,
            query="contradictory empty search",
            language=SupportedLanguage.ENGLISH,
            results=[],
            total=1,
        )

    with pytest.raises(
        ValidationError,
        match="results search must contain evidence",
    ):
        SearchResponse(
            outcome=SearchOutcome.RESULTS,
            query="missing results",
            language=SupportedLanguage.ENGLISH,
            results=[],
            total=0,
        )


def test_citations_and_answer_requests_reject_duplicate_evidence() -> None:
    citation = Citation.model_validate(citation_payload())

    assert citation.evidence_ids == ["synthetic-object-001"]

    duplicate_citation = citation_payload()
    duplicate_citation["evidence_ids"] = [
        "synthetic-object-001",
        "synthetic-object-001",
    ]

    with pytest.raises(
        ValidationError,
        match="Citation evidence identifiers must be unique",
    ):
        Citation.model_validate(duplicate_citation)

    request = AnswerRequest.model_validate(
        {
            "question": "What does the synthetic evidence show?",
            "language": "en",
            "evidence_ids": ["synthetic-object-001"],
        }
    )

    assert request.evidence_ids == ["synthetic-object-001"]

    with pytest.raises(
        ValidationError,
        match="Answer evidence identifiers must be unique",
    ):
        AnswerRequest.model_validate(
            {
                "question": "Duplicate evidence",
                "language": "en",
                "evidence_ids": [
                    "synthetic-object-001",
                    "synthetic-object-001",
                ],
            }
        )


def test_answer_response_union_validates_all_outcomes() -> None:
    adapter: TypeAdapter[AnswerResponse] = TypeAdapter(AnswerResponse)

    answered = adapter.validate_python(
        {
            "outcome": "answered",
            "question": "What does the synthetic evidence show?",
            "language": "en",
            "answer_text": "The synthetic record describes a poster. [1]",
            "citations": [citation_payload()],
            "limitations": ["This answer uses synthetic development evidence only."],
        }
    )
    abstained = adapter.validate_python(
        {
            "outcome": "abstained",
            "question": "What did everyone think?",
            "language": "en",
            "answer_text": None,
            "citations": [],
            "reason": "unsupported_question",
            "limitations": [
                "The supplied evidence cannot support a population-wide claim."
            ],
        }
    )
    unavailable = adapter.validate_python(
        {
            "outcome": "generation_unavailable",
            "question": "Summarize the synthetic record.",
            "language": "en",
            "answer_text": None,
            "citations": [],
            "reason": "not_configured",
            "limitations": [
                "Answer generation is unavailable; search results remain usable."
            ],
        }
    )

    assert isinstance(answered, AnsweredResponse)
    assert isinstance(abstained, AbstainedResponse)
    assert isinstance(unavailable, GenerationUnavailableResponse)

    schema = adapter.json_schema()
    assert schema["discriminator"]["propertyName"] == "outcome"

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "outcome": "answered",
                "question": "Invalid answer",
                "language": "en",
                "answer_text": "This answer has no citation.",
                "citations": [],
            }
        )


def test_structured_error_response_has_stable_code() -> None:
    response = ErrorResponse.model_validate(
        {
            "error": {
                "code": "invalid_request",
                "message": "The request could not be validated.",
                "field_errors": [
                    {
                        "field": "language",
                        "message": "Expected en, fr, or nl.",
                    }
                ],
                "request_id": "request-001",
            }
        }
    )

    assert response.error.code is ErrorCode.INVALID_REQUEST
    assert response.error.field_errors[0].field == "language"
    assert response.error.request_id == "request-001"
