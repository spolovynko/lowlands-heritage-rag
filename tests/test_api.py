from collections.abc import Sequence

from fastapi.testclient import TestClient

from lowlands_lens.api.app import create_app
from lowlands_lens.application.answer_generation import (
    AnswerResult,
    GeneratedAnswer,
    GeneratedCitation,
)
from lowlands_lens.application.retrieval import RetrievalQuery, RetrievalResult
from lowlands_lens.application.services import ApplicationServices
from lowlands_lens.domain import EvidenceRecord, Language


def client() -> TestClient:
    return TestClient(create_app())


def test_health_and_openapi_expose_the_versioned_contract() -> None:
    test_client = client()

    health = test_client.get("/api/v1/health")
    schema = test_client.get("/openapi.json").json()

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "contract_version": "1.0.0"}
    assert schema["info"]["version"] == "1.0.0"
    assert set(schema["paths"]) >= {
        "/api/v1/health",
        "/api/v1/search",
        "/api/v1/answer",
    }


def test_search_success_exposes_evidence_provenance_and_rights() -> None:
    response = client().post(
        "/api/v1/search",
        json={"query": "poster", "language": "en", "limit": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "results"
    assert payload["total"] == 1
    record = payload["results"][0]
    assert record["is_synthetic"] is True
    assert {provider["role"] for provider in record["providers"]} == {
        "provider",
        "data_provider",
    }
    assert {statement["scope"] for statement in record["rights"]} == {
        "metadata",
        "digital_object",
    }
    assert record["source_links"]


def test_empty_search_is_a_successful_outcome() -> None:
    response = client().post(
        "/api/v1/search",
        json={"query": "no matching object", "language": "en"},
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "empty"
    assert response.json()["results"] == []


def test_retrieval_failure_uses_the_structured_error_contract() -> None:
    response = client().post(
        "/api/v1/search",
        json={"query": "simulate-search-error", "language": "en"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "search_unavailable"


def test_invalid_request_uses_the_structured_error_contract() -> None:
    response = client().post(
        "/api/v1/search",
        json={"query": "poster", "language": "de", "limit": 0},
    )

    assert response.status_code == 422
    payload = response.json()["error"]
    assert payload["code"] == "invalid_request"
    assert {error["field"] for error in payload["field_errors"]} == {
        "language",
        "limit",
    }


def test_answer_endpoint_exposes_every_answer_outcome() -> None:
    test_client = client()
    base_request = {
        "language": "en",
        "evidence_ids": ["synthetic-poster-001"],
    }

    answered = test_client.post(
        "/api/v1/answer",
        json={**base_request, "question": "What does this record demonstrate?"},
    )
    abstained = test_client.post(
        "/api/v1/answer",
        json={
            **base_request,
            "question": "Who was objectively the most influential Belgian artist?",
        },
    )
    unavailable = test_client.post(
        "/api/v1/answer",
        json={**base_request, "question": "simulate-generation-unavailable"},
    )

    assert answered.status_code == 200
    assert answered.json()["outcome"] == "answered"
    assert answered.json()["citations"][0]["evidence_ids"] == ["synthetic-poster-001"]
    assert abstained.json()["outcome"] == "abstained"
    assert abstained.json()["answer_text"] is None
    assert unavailable.json()["outcome"] == "generation_unavailable"
    assert unavailable.json()["answer_text"] is None


def test_answer_rejects_unknown_evidence_through_a_structured_error() -> None:
    response = client().post(
        "/api/v1/answer",
        json={
            "question": "What does this show?",
            "language": "en",
            "evidence_ids": ["unknown-record"],
        },
    )

    assert response.status_code == 404
    payload = response.json()["error"]
    assert payload["code"] == "not_found"
    assert payload["field_errors"][0]["field"] == "evidence_ids"


class EmptyRetriever:
    def search(self, query: RetrievalQuery) -> RetrievalResult:
        return RetrievalResult(records=(), total=0, limitations=(query.text,))


class EmptyRepository:
    def get_by_ids(self, evidence_ids: Sequence[str]) -> tuple[EvidenceRecord, ...]:
        return ()


class StubAnswerGenerator:
    def generate(
        self,
        question: str,
        language: Language,
        evidence: tuple[EvidenceRecord, ...],
    ) -> AnswerResult:
        return GeneratedAnswer(
            text=f"{question} ({language.value})",
            citations=(GeneratedCitation(label="stub", evidence_ids=("stub",)),),
        )


def test_application_factory_accepts_replaceable_components() -> None:
    services = ApplicationServices(
        retriever=EmptyRetriever(),
        evidence_repository=EmptyRepository(),
        answer_generator=StubAnswerGenerator(),
    )
    response = TestClient(create_app(services)).post(
        "/api/v1/search",
        json={"query": "adapter proof", "language": "en"},
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "empty"
    assert response.json()["limitations"] == ["adapter proof"]
