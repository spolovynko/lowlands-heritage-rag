from typing import Final

from fastapi import FastAPI

API_V1_PREFIX: Final = "/api/v1"
API_CONTRACT_VERSION: Final = "1.0.0"

def create_app() -> FastAPI:
    app = FastAPI(
        title="Lowlands Lens API",
        version=API_CONTRACT_VERSION,
        description="API for Lowlands Lens",
    )
    return app

app = create_app()