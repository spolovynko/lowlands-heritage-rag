"""Version 1 HTTP routes for the Lowlands Lens application."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lowlands_lens.api.constants import API_CONTRACT_VERSION, API_V1_PREFIX
from lowlands_lens.api.contracts import (
    AnswerRequest,
    AnswerResponse,
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    FieldError,
    HealthResponse,
    SearchOutcome,
    SearchRequest,
    SearchResponse,
)
from lowlands_lens.api.mappers import to_answer_contract, to_evidence_contract
from lowlands_lens.application.retrieval import (
    RetrievalQuery,
    RetrievalUnavailableError,
)
from lowlands_lens.application.services import ApplicationServices
from lowlands_lens.domain import Language


def create_api_router(services: ApplicationServices) -> APIRouter:
    """Create routes whose dependencies are supplied explicitly."""
    router = APIRouter(prefix=API_V1_PREFIX)

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(contract_version=API_CONTRACT_VERSION)

    @router.post(
        "/search",
        response_model=SearchResponse,
        responses={503: {"model": ErrorResponse}},
    )
    def search(request: SearchRequest) -> SearchResponse | JSONResponse:
        language = Language(request.language.value)
        try:
            result = services.retriever.search(
                RetrievalQuery(
                    text=request.query,
                    language=language,
                    limit=request.limit,
                )
            )
        except RetrievalUnavailableError:
            return error_json_response(
                status_code=503,
                code=ErrorCode.SEARCH_UNAVAILABLE,
                message="Search is temporarily unavailable in the Phase 2 prototype.",
            )

        evidence = [to_evidence_contract(record) for record in result.records]
        return SearchResponse(
            outcome=SearchOutcome.RESULTS if evidence else SearchOutcome.EMPTY,
            query=request.query,
            language=request.language,
            results=evidence,
            total=result.total,
            limitations=list(result.limitations),
        )

    @router.post(
        "/answer",
        response_model=AnswerResponse,
        responses={404: {"model": ErrorResponse}},
    )
    def answer(request: AnswerRequest) -> AnswerResponse | JSONResponse:
        records = services.evidence_repository.get_by_ids(request.evidence_ids)
        found_ids = {record.evidence_id for record in records}
        missing_ids = [
            evidence_id
            for evidence_id in request.evidence_ids
            if evidence_id not in found_ids
        ]
        if missing_ids:
            return error_json_response(
                status_code=404,
                code=ErrorCode.NOT_FOUND,
                message="One or more selected evidence records were not found.",
                field_errors=[
                    FieldError(
                        field="evidence_ids",
                        message=f"Unknown identifier: {evidence_id}",
                    )
                    for evidence_id in missing_ids
                ],
            )

        language = Language(request.language.value)
        result = services.answer_generator.generate(
            question=request.question,
            language=language,
            evidence=records,
        )
        return to_answer_contract(
            result,
            question=request.question,
            language=language,
        )

    return router


def error_json_response(
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    field_errors: list[FieldError] | None = None,
) -> JSONResponse:
    """Serialize every operational error through the public error contract."""
    response = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            field_errors=field_errors or [],
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )
