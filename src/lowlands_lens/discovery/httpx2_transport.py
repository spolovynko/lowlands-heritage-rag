"""HTTPX2 adapter for the discovery HTTP transport port."""

from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Final, Self

import httpx2

from lowlands_lens.discovery.transport import (
    HttpResponse,
    TransportRequestError,
    TransportTimeoutError,
)

CONNECT_TIMEOUT_SECONDS: Final = 5.0
READ_TIMEOUT_SECONDS: Final = 15.0
WRITE_TIMEOUT_SECONDS: Final = 5.0
POOL_TIMEOUT_SECONDS: Final = 5.0


class Httpx2Transport:
    """Synchronous HTTPX2 implementation with bounded resources."""

    def __init__(
        self,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        timeout = httpx2.Timeout(
            connect=CONNECT_TIMEOUT_SECONDS,
            read=READ_TIMEOUT_SECONDS,
            write=WRITE_TIMEOUT_SECONDS,
            pool=POOL_TIMEOUT_SECONDS,
        )
        limits = httpx2.Limits(
            max_connections=1,
            max_keepalive_connections=1,
        )
        self._client = httpx2.Client(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            transport=transport,
        )

    def get(
        self,
        url: str,
        *,
        params: Sequence[tuple[str, str]],
        headers: Mapping[str, str],
    ) -> HttpResponse:
        """Perform one request and hide HTTPX2-specific response types."""
        try:
            response = self._client.get(
                url,
                params=list(params),
                headers=dict(headers),
            )
        except httpx2.TimeoutException:
            raise TransportTimeoutError("The HTTP transport timed out.") from None
        except httpx2.RequestError:
            raise TransportRequestError(
                "The HTTP transport could not complete the request."
            ) from None

        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
        )

    def close(self) -> None:
        """Release the owned connection pool."""
        self._client.close()

    def __enter__(self) -> Self:
        """Enter a bounded transport lifetime."""
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Always release resources when leaving the context."""
        self.close()
