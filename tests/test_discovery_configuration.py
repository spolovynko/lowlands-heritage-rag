import pytest

from lowlands_lens.discovery.configuration import (
    EUROPEANA_API_KEY_ENV,
    EUROPEANA_API_KEY_HEADER,
    EuropeanaCredentials,
    MissingEuropeanaCredentialError,
)


def test_credentials_use_the_application_owned_environment_boundary() -> None:
    credentials = EuropeanaCredentials.from_environment(
        {EUROPEANA_API_KEY_ENV: "  fake-local-test-key  "}
    )

    assert EUROPEANA_API_KEY_ENV == "LOWLANDS_LENS_EUROPEANA_API_KEY"
    assert EUROPEANA_API_KEY_HEADER == "X-Api-Key"
    assert credentials.api_key == "fake-local-test-key"


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {EUROPEANA_API_KEY_ENV: ""},
        {EUROPEANA_API_KEY_ENV: "   "},
    ],
)
def test_missing_or_blank_credentials_fail_without_a_secret(
    environ: dict[str, str],
) -> None:
    with pytest.raises(
        MissingEuropeanaCredentialError,
        match=EUROPEANA_API_KEY_ENV,
    ):
        EuropeanaCredentials.from_environment(environ)


def test_credential_string_representations_are_redacted() -> None:
    secret = "fake-secret-that-must-not-appear"
    credentials = EuropeanaCredentials(api_key=secret)

    assert repr(credentials) == "EuropeanaCredentials(api_key=<redacted>)"
    assert str(credentials) == "EuropeanaCredentials(api_key=<redacted>)"
    assert secret not in repr(credentials)
    assert secret not in str(credentials)


def test_direct_construction_rejects_a_blank_key() -> None:
    with pytest.raises(
        MissingEuropeanaCredentialError,
        match="non-empty API key",
    ):
        EuropeanaCredentials(api_key="  ")
