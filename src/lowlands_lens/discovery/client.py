"""Focused Search and Record client for Phase 3 discovery."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, TypeVar, cast
from urllib.parse import quote

from pydantic import BaseModel, ValidationError

from lowlands_lens.discovery.configuration import (
    EUROPEANA_API_KEY_HEADER,
    EuropeanaCredentials,
)
from lowlands_lens.discovery.contracts import (
    EuropeanaRecordResponsePayload,
    EuropeanaSearchResponsePayload,
    RecordRequestConfiguration,
    SearchRequestConfiguration,
)
from lowlands_lens.discovery.transport import (
    HttpResponse,
    HttpTransport,
    TransportRequestError,
    TransportTimeoutError,
)

SEARCH_ENDPOINT: Final = "https://api.europeana.eu/record/v2/search.json"
RECORD_ENDPOINT_ROOT: Final = "https://api.europeana.eu/record/v2"
USER_AGENT: Final = "Lowlands-Lens/0.1 Phase-3-Discovery"

PayloadT = TypeVar("PayloadT", bound=BaseModel)
SENSITIVE_JSON_FIELDS: Final = frozenset({"apikey", "x-api-key", "wskey"})


@dataclass(frozen=True, slots=True)
class EuropeanaRecordSnapshot:
    """Validated record plus a recursively redacted raw API document."""

    parsed: EuropeanaRecordResponsePayload
    sanitized_document: dict[str, object]


class EuropeanaClientError(RuntimeError):
    """Base for sanitized Europeana discovery failures."""


class EuropeanaTimeoutError(EuropeanaClientError):
    """Raised when a bounded Europeana request times out."""


class EuropeanaTransportError(EuropeanaClientError):
    """Raised when the network transport cannot complete a request."""


class EuropeanaAuthenticationError(EuropeanaClientError):
    """Raised when Europeana rejects the configured credential."""


class EuropeanaRecordNotFoundError(EuropeanaClientError):
    """Raised when a requested Europeana record does not exist."""


class EuropeanaInvalidJsonError(EuropeanaClientError):
    """Raised when Europeana does not return valid JSON."""


class EuropeanaInvalidResponseError(EuropeanaClientError):
    """Raised when JSON does not satisfy the exploration contracts."""


class EuropeanaRateLimitError(EuropeanaClientError):
    """Raised when Europeana responds with HTTP 429."""

    def __init__(self, retry_after_seconds: int | None) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Europeana temporarily rate limited the discovery request.")


class EuropeanaHttpStatusError(EuropeanaClientError):
    """Raised for an unclassified non-successful HTTP status."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Europeana returned HTTP status {status_code}.")


class EuropeanaDiscoveryClient:
    """Bounded client for Search and Record API exploration."""

    def __init__(
        self,
        transport: HttpTransport,
        credentials: EuropeanaCredentials,
    ) -> None:
        self._transport = transport
        self._credentials = credentials

    def search(
        self,
        request: SearchRequestConfiguration,
    ) -> EuropeanaSearchResponsePayload:
        """Execute one bounded Search API request."""
        params: list[tuple[str, str]] = [
            ("query", request.query),
            ("profile", request.profile),
            ("rows", str(request.rows)),
        ]
        params.extend(("qf", value) for value in request.refinements)
        params.extend(("facet", value) for value in request.facets)

        if request.reusability is not None:
            params.append(("reusability", request.reusability))

        if request.start is not None:
            params.append(("start", str(request.start)))
        if request.cursor is not None:
            params.append(("cursor", request.cursor))

        response = self._get(SEARCH_ENDPOINT, params)
        return self._parse_payload(response, EuropeanaSearchResponsePayload)

    def record(
        self,
        request: RecordRequestConfiguration,
    ) -> EuropeanaRecordResponsePayload:
        """Retrieve one complete record selected during discovery."""
        return self.record_snapshot(request).parsed

    def record_snapshot(
        self,
        request: RecordRequestConfiguration,
    ) -> EuropeanaRecordSnapshot:
        """Retrieve one record with a safe local raw-snapshot representation."""
        identifier = request.record_id.removeprefix("/")
        dataset_id, local_id = identifier.split("/", maxsplit=1)
        url = (
            f"{RECORD_ENDPOINT_ROOT}/"
            f"{quote(dataset_id, safe='')}/{quote(local_id, safe='')}.json"
        )
        response = self._get(url, ())
        document = self._decode_document(response)
        parsed = self._validate_payload(document, EuropeanaRecordResponsePayload)
        sanitized = self._redact_json(document)
        if not isinstance(sanitized, dict):
            raise EuropeanaInvalidResponseError(
                "Europeana returned an unexpected JSON structure."
            )
        return EuropeanaRecordSnapshot(
            parsed=parsed,
            sanitized_document=cast(dict[str, object], sanitized),
        )

    def _get(
        self,
        url: str,
        params: Sequence[tuple[str, str]],
    ) -> HttpResponse:
        headers = {
            EUROPEANA_API_KEY_HEADER: self._credentials.api_key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        try:
            response = self._transport.get(url, params=params, headers=headers)
        except TransportTimeoutError:
            raise EuropeanaTimeoutError(
                "Europeana did not respond within the configured timeout."
            ) from None
        except TransportRequestError:
            raise EuropeanaTransportError(
                "The Europeana request could not be completed."
            ) from None

        self._raise_for_status(response)
        return response

    @classmethod
    def _raise_for_status(cls, response: HttpResponse) -> None:
        status_code = response.status_code
        if 200 <= status_code < 300:
            return
        if status_code in {401, 403}:
            raise EuropeanaAuthenticationError(
                "Europeana rejected the configured credential."
            )
        if status_code == 404:
            raise EuropeanaRecordNotFoundError(
                "The requested Europeana record was not found."
            )
        if status_code == 429:
            raise EuropeanaRateLimitError(cls._retry_after_seconds(response.headers))
        raise EuropeanaHttpStatusError(status_code)

    @staticmethod
    def _retry_after_seconds(headers: Mapping[str, str]) -> int | None:
        for name, value in headers.items():
            if name.casefold() == "retry-after" and value.strip().isdigit():
                return int(value.strip())
        return None

    @staticmethod
    def _parse_payload(
        response: HttpResponse,
        model_type: type[PayloadT],
    ) -> PayloadT:
        document = EuropeanaDiscoveryClient._decode_document(response)
        return EuropeanaDiscoveryClient._validate_payload(document, model_type)

    @staticmethod
    def _decode_document(response: HttpResponse) -> dict[str, object]:
        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError, UnicodeDecodeError:
            raise EuropeanaInvalidJsonError(
                "Europeana returned invalid JSON."
            ) from None
        if not isinstance(payload, dict):
            raise EuropeanaInvalidResponseError(
                "Europeana returned an unexpected JSON structure."
            )
        return cast(dict[str, object], payload)

    @staticmethod
    def _validate_payload(
        document: dict[str, object],
        model_type: type[PayloadT],
    ) -> PayloadT:
        try:
            return model_type.model_validate(document)
        except ValidationError:
            raise EuropeanaInvalidResponseError(
                "Europeana returned JSON that does not match the exploration contract."
            ) from None

    @staticmethod
    def _redact_json(value: object) -> object:
        if isinstance(value, dict):
            redacted: dict[str, object] = {}
            for key, nested_value in value.items():
                key_text = str(key)
                if key_text.casefold() in SENSITIVE_JSON_FIELDS:
                    redacted[key_text] = "<redacted>"
                else:
                    redacted[key_text] = EuropeanaDiscoveryClient._redact_json(
                        nested_value
                    )
            return redacted
        if isinstance(value, list):
            return [EuropeanaDiscoveryClient._redact_json(item) for item in value]
        return value
