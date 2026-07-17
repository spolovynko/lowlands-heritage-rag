"""Stable API and package-owned interface constants."""

from pathlib import Path
from typing import Final

API_V1_PREFIX: Final = "/api/v1"
API_CONTRACT_VERSION: Final = "1.0.0"
STATIC_DIRECTORY: Final = Path(__file__).parent / "static"
INDEX_FILE: Final = STATIC_DIRECTORY / "index.html"
