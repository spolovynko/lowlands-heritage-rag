"""HTTP transport port for bounded Europeana discovery."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Library-independent HTTP response data needed by discovery."""

    status_code: int
    headers: Mapping[str, str]
    content: bytes


class TransportTimeoutError(RuntimeError):
    """Raised when the HTTP transport exceeds a configured timeout."""


class TransportRequestError(RuntimeError):
    """Raised when the transport cannot complete an HTTP request."""


class HttpTransport(Protocol):
    """Small synchronous HTTP port required by Europeana discovery."""

    def get(
        self,
        url: str,
        *,
        params: Sequence[tuple[str, str]],
        headers: Mapping[str, str],
    ) -> HttpResponse:
        """Perform one bounded GET request."""
        ...
