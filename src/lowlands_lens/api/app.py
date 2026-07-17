"""FastAPI application factory and default local application."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lowlands_lens.adapters.deterministic_answer_generation import (
    DeterministicAnswerGenerator,
)
from lowlands_lens.adapters.in_memory_retrieval import InMemoryRetrievalAdapter
from lowlands_lens.adapters.synthetic_records import SYNTHETIC_FIXTURES
from lowlands_lens.api.constants import (
    API_CONTRACT_VERSION,
    INDEX_FILE,
    STATIC_DIRECTORY,
)
from lowlands_lens.api.contracts import ErrorCode, FieldError
from lowlands_lens.api.routes import create_api_router, error_json_response
from lowlands_lens.application.services import ApplicationServices


def create_default_services() -> ApplicationServices:
    """Build the credential-free deterministic Phase 2 adapters."""
    retrieval = InMemoryRetrievalAdapter(SYNTHETIC_FIXTURES)
    return ApplicationServices(
        retriever=retrieval,
        evidence_repository=retrieval,
        answer_generator=DeterministicAnswerGenerator(),
    )


def create_app(services: ApplicationServices | None = None) -> FastAPI:
    """Create an application with replaceable dependencies."""
    app = FastAPI(
        title="Lowlands Lens API",
        version=API_CONTRACT_VERSION,
        description=(
            "Versioned Phase 2 API for a deterministic synthetic cultural-heritage "
            "journey."
        ),
    )
    selected_services = services or create_default_services()
    app.include_router(create_api_router(selected_services))
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")

    @app.get("/", include_in_schema=False)
    def interface() -> FileResponse:
        return FileResponse(INDEX_FILE)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        field_errors = [
            FieldError(
                field=".".join(str(part) for part in error["loc"] if part != "body"),
                message=str(error["msg"]),
            )
            for error in exception.errors()
        ]
        return error_json_response(
            status_code=422,
            code=ErrorCode.INVALID_REQUEST,
            message="The request did not match the API contract.",
            field_errors=field_errors,
        )

    return app


app = create_app()
