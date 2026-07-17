"""Secure configuration boundary for Europeana source discovery."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

EUROPEANA_API_KEY_ENV: Final = "LOWLANDS_LENS_EUROPEANA_API_KEY"
EUROPEANA_API_KEY_HEADER: Final = "X-Api-Key"


class MissingEuropeanaCredentialError(RuntimeError):
    """Raised when Europeana discovery has no usable API credential."""


@dataclass(frozen=True, slots=True, repr=False)
class EuropeanaCredentials:
    """Validated Europeana credentials whose representation is always redacted."""

    api_key: str

    def __post_init__(self) -> None:
        """Normalize the key and reject blank direct construction."""
        normalized_key = self.api_key.strip()
        if not normalized_key:
            raise MissingEuropeanaCredentialError(
                "Europeana discovery requires a non-empty API key."
            )
        object.__setattr__(self, "api_key", normalized_key)

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> EuropeanaCredentials:
        """Load the application-owned Europeana key from an injected environment."""
        source = os.environ if environ is None else environ
        value = source.get(EUROPEANA_API_KEY_ENV)
        if value is None or not value.strip():
            raise MissingEuropeanaCredentialError(
                f"{EUROPEANA_API_KEY_ENV} must be set to a non-empty value."
            )
        return cls(api_key=value)

    def __repr__(self) -> str:
        """Prevent accidental disclosure in diagnostics and containers."""
        return "EuropeanaCredentials(api_key=<redacted>)"

    def __str__(self) -> str:
        """Prevent accidental disclosure in user-facing string conversion."""
        return repr(self)
