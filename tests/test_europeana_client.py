"""Credential-free tests for the bounded Europeana client."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx2
import pytest

from lowlands_lens.discovery.client import (
    SEARCH_ENDPOINT,
    EuropeanaAuthenticationError,
    EuropeanaDiscoveryClient,
    EuropeanaHttpStatusError,
    EuropeanaInvalidJsonError,
    EuropeanaInvalidResponseError,
    EuropeanaRateLimitError,
    EuropeanaRecordNotFoundError,
    EuropeanaTimeoutError,
    EuropeanaTransportError,
)
from lowlands_lens.discovery.configuration import EuropeanaCredentials
from lowlands_lens.discovery.contracts import (
    RecordRequestConfiguration,
    SearchRequestConfiguration,
)
from lowlands_lens.discovery.httpx2_transport import Httpx2Transport
from lowlands_lens.discovery.transport import (
    HttpResponse,
    TransportRequestError,
    TransportTimeoutError,
)

FAKE_KEY = "fake-test-key-never-a-real-credential"


@dataclass(frozen=True, slots=True)
class CapturedRequest:
    """One request observed by the fake transport."""

    url: str
    params: tuple[tuple[str, str], ...]
    headers: Mapping[str, str]


class RecordingTransport:
    """Deterministic transport that performs no network access."""

    def __init__(
        self,
        response: HttpResponse,
        failure: TransportTimeoutError | TransportRequestError | None = None,
    ) -> None:
        self._response = response
        self._failure = failure
        self.requests: list[CapturedRequest] = []

    def get(
        self,
        url: str,
        *,
        params: Sequence[tuple[str, str]],
        headers: Mapping[str, str],
    ) -> HttpResponse:
        self.requests.append(CapturedRequest(url, tuple(params), dict(headers)))
        if self._failure is not None:
            raise self._failure
        return self._response


def json_response(
    payload: object,
    *,
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
) -> HttpResponse:
    """Build one sanitized JSON response for a fake transport."""
    return HttpResponse(
        status_code=status_code,
        headers={} if headers is None else headers,
        content=json.dumps(payload).encode("utf-8"),
    )


def search_request(**overrides: object) -> SearchRequestConfiguration:
    """Build one valid request with explicitly bounded defaults."""
    payload: dict[str, object] = {
        "query_id": "places-en-001",
        "query": "Brussels & Antwerp",
        "refinements": ("YEAR:[1900 TO 2026]",),
        "facets": ("TYPE", "LANGUAGE"),
        "rows": 12,
        "sample_limit": 6,
    }
    payload.update(overrides)
    return SearchRequestConfiguration.model_validate(payload)


def test_search_builds_repeatable_parameters_and_header_authentication() -> None:
    transport = RecordingTransport(
        json_response(
            {
                "success": True,
                "itemsCount": 1,
                "totalResults": 1,
                "items": [{"id": "/123/example", "title": ["Brussels"]}],
                "facets": [],
            }
        )
    )
    client = EuropeanaDiscoveryClient(
        transport,
        EuropeanaCredentials(FAKE_KEY),
    )

    response = client.search(search_request(start=1))
    captured = transport.requests[0]

    assert response.items[0].record_id == "/123/example"
    assert captured.url == SEARCH_ENDPOINT
    assert captured.params == (
        ("query", "Brussels & Antwerp"),
        ("profile", "facets"),
        ("rows", "12"),
        ("qf", "YEAR:[1900 TO 2026]"),
        ("facet", "TYPE"),
        ("facet", "LANGUAGE"),
        ("start", "1"),
    )
    assert captured.headers["X-Api-Key"] == FAKE_KEY
    assert captured.headers["Accept"] == "application/json"
    assert "Lowlands-Lens" in captured.headers["User-Agent"]
    assert all(name != "wskey" for name, _ in captured.params)


def test_cursor_is_preserved_without_basic_pagination() -> None:
    transport = RecordingTransport(
        json_response(
            {
                "success": True,
                "itemsCount": 0,
                "totalResults": 0,
            }
        )
    )
    client = EuropeanaDiscoveryClient(transport, EuropeanaCredentials(FAKE_KEY))

    response = client.search(search_request(cursor="*"))

    assert response.items == []
    assert ("cursor", "*") in transport.requests[0].params
    assert not any(name == "start" for name, _ in transport.requests[0].params)


def test_reusability_uses_its_dedicated_parameter() -> None:
    transport = RecordingTransport(
        json_response({"success": True, "itemsCount": 0, "totalResults": 0})
    )
    client = EuropeanaDiscoveryClient(transport, EuropeanaCredentials(FAKE_KEY))

    client.search(search_request(reusability="open"))

    assert ("reusability", "open") in transport.requests[0].params
    assert not any(
        name == "qf" and value == "REUSABILITY:open"
        for name, value in transport.requests[0].params
    )


def test_record_identifier_is_encoded_as_path_data() -> None:
    transport = RecordingTransport(
        json_response(
            {
                "success": True,
                "object": {
                    "about": "/123/local id/part",
                    "proxies": [],
                    "aggregations": [],
                },
            }
        )
    )
    client = EuropeanaDiscoveryClient(transport, EuropeanaCredentials(FAKE_KEY))

    response = client.record(RecordRequestConfiguration(record_id="/123/local id/part"))

    assert response.record_object.about == "/123/local id/part"
    assert transport.requests[0].url.endswith("/123/local%20id%2Fpart.json")
    assert transport.requests[0].params == ()


def test_record_snapshot_recursively_redacts_sensitive_fields() -> None:
    transport = RecordingTransport(
        json_response(
            {
                "success": True,
                "apikey": FAKE_KEY,
                "object": {
                    "about": "/123/example",
                    "proxies": [],
                    "aggregations": [],
                    "nested": {"wskey": FAKE_KEY},
                },
            }
        )
    )
    client = EuropeanaDiscoveryClient(transport, EuropeanaCredentials(FAKE_KEY))

    snapshot = client.record_snapshot(
        RecordRequestConfiguration(record_id="/123/example")
    )
    serialized = json.dumps(snapshot.sanitized_document)

    assert snapshot.parsed.record_object.about == "/123/example"
    assert FAKE_KEY not in serialized
    assert snapshot.sanitized_document["apikey"] == "<redacted>"
    assert "<redacted>" in serialized


@pytest.mark.parametrize(
    ("response", "expected_exception"),
    [
        (HttpResponse(200, {}, b"not-json"), EuropeanaInvalidJsonError),
        (json_response(["unexpected"]), EuropeanaInvalidResponseError),
        (
            json_response({"success": True, "itemsCount": "invalid"}),
            EuropeanaInvalidResponseError,
        ),
    ],
)
def test_invalid_success_responses_are_sanitized(
    response: HttpResponse,
    expected_exception: type[Exception],
) -> None:
    client = EuropeanaDiscoveryClient(
        RecordingTransport(response),
        EuropeanaCredentials(FAKE_KEY),
    )

    with pytest.raises(expected_exception) as captured:
        client.search(search_request())

    assert FAKE_KEY not in str(captured.value)
    assert "not-json" not in str(captured.value)


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (401, EuropeanaAuthenticationError),
        (403, EuropeanaAuthenticationError),
        (404, EuropeanaRecordNotFoundError),
        (500, EuropeanaHttpStatusError),
    ],
)
def test_http_statuses_have_structured_sanitized_exceptions(
    status_code: int,
    expected_exception: type[Exception],
) -> None:
    response = HttpResponse(
        status_code,
        {},
        f'{{"apikey":"{FAKE_KEY}"}}'.encode(),
    )
    client = EuropeanaDiscoveryClient(
        RecordingTransport(response),
        EuropeanaCredentials(FAKE_KEY),
    )

    with pytest.raises(expected_exception) as captured:
        client.search(search_request())

    assert FAKE_KEY not in str(captured.value)
    assert FAKE_KEY not in repr(captured.value)


def test_rate_limit_preserves_only_numeric_retry_guidance() -> None:
    client = EuropeanaDiscoveryClient(
        RecordingTransport(HttpResponse(429, {"Retry-After": "30"}, b"ignored")),
        EuropeanaCredentials(FAKE_KEY),
    )

    with pytest.raises(EuropeanaRateLimitError) as captured:
        client.search(search_request())

    assert captured.value.retry_after_seconds == 30


@pytest.mark.parametrize(
    ("failure", "expected_exception"),
    [
        (TransportTimeoutError("unsafe-detail"), EuropeanaTimeoutError),
        (TransportRequestError("unsafe-detail"), EuropeanaTransportError),
    ],
)
def test_transport_failures_are_mapped_without_original_details(
    failure: TransportTimeoutError | TransportRequestError,
    expected_exception: type[Exception],
) -> None:
    client = EuropeanaDiscoveryClient(
        RecordingTransport(json_response({}), failure),
        EuropeanaCredentials(FAKE_KEY),
    )

    with pytest.raises(expected_exception) as captured:
        client.search(search_request())

    assert "unsafe-detail" not in str(captured.value)
    assert FAKE_KEY not in str(captured.value)


def test_httpx2_adapter_supports_mock_transport_without_network() -> None:
    observed: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        observed.append(request)
        return httpx2.Response(200, json={"success": True})

    with Httpx2Transport(httpx2.MockTransport(handler)) as transport:
        response = transport.get(
            "https://example.invalid/search",
            params=(("facet", "TYPE"), ("facet", "LANGUAGE")),
            headers={"X-Api-Key": FAKE_KEY},
        )

    assert response.status_code == 200
    assert observed[0].headers["X-Api-Key"] == FAKE_KEY
    assert observed[0].url.params.multi_items() == [
        ("facet", "TYPE"),
        ("facet", "LANGUAGE"),
    ]
