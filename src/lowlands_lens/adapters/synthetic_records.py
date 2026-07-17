"""Deterministic, clearly labelled synthetic Phase 2 records."""

from dataclasses import dataclass
from typing import Final

from lowlands_lens.domain import (
    EvidenceRecord,
    LocalizedValue,
    MediaType,
    ProviderRecord,
    ProviderRole,
    RightsRecord,
    RightsScope,
    RightsStatus,
    SourceLinkKind,
    SourceLinkRecord,
)


@dataclass(frozen=True, slots=True)
class SyntheticFixture:
    """Evidence plus private matching terms used only by the mock retriever."""

    evidence: EvidenceRecord
    search_terms: tuple[str, ...]


METADATA_RIGHTS: Final = RightsRecord(
    scope=RightsScope.METADATA,
    status=RightsStatus.KNOWN,
    label="CC0 1.0 (synthetic metadata fixture)",
    uri="https://creativecommons.org/publicdomain/zero/1.0/",
)

SYNTHETIC_FIXTURES: Final[tuple[SyntheticFixture, ...]] = (
    SyntheticFixture(
        evidence=EvidenceRecord(
            evidence_id="synthetic-poster-001",
            is_synthetic=True,
            titles=(
                LocalizedValue("Poster for a fictional 1958 design fair", "en"),
                LocalizedValue("Affiche voor een fictieve ontwerpbeurs", "nl"),
                LocalizedValue("Affiche pour une foire fictive du design", "fr"),
            ),
            descriptions=(
                LocalizedValue(
                    "A synthetic geometric poster created to demonstrate "
                    "multilingual titles, provider attribution, and known rights.",
                    "en",
                ),
            ),
            media_type=MediaType.IMAGE,
            object_type="Poster",
            date_display="1958 (fictional)",
            providers=(
                ProviderRecord(
                    provider_id="synthetic-provider-aggregator",
                    name="Synthetic Lowlands Aggregator",
                    role=ProviderRole.PROVIDER,
                    homepage_url="https://example.org/lowlands-lens/aggregator",
                ),
                ProviderRecord(
                    provider_id="synthetic-provider-design",
                    name="Synthetic Belgian Design Collection",
                    role=ProviderRole.DATA_PROVIDER,
                    homepage_url="https://example.org/lowlands-lens/design",
                ),
            ),
            source_links=(
                SourceLinkRecord(
                    kind=SourceLinkKind.RECORD,
                    label="Synthetic record page",
                    url="https://example.org/lowlands-lens/records/poster-001",
                ),
                SourceLinkRecord(
                    kind=SourceLinkKind.DIGITAL_OBJECT,
                    label="Synthetic digital object",
                    url="https://example.org/lowlands-lens/objects/poster-001",
                ),
            ),
            rights=(
                METADATA_RIGHTS,
                RightsRecord(
                    scope=RightsScope.DIGITAL_OBJECT,
                    status=RightsStatus.KNOWN,
                    label="CC BY 4.0 (synthetic fixture)",
                    uri="https://creativecommons.org/licenses/by/4.0/",
                ),
            ),
        ),
        search_terms=(
            "poster",
            "affiche",
            "design",
            "ontwerp",
            "1958",
            "graphic",
            "grafisch",
        ),
    ),
    SyntheticFixture(
        evidence=EvidenceRecord(
            evidence_id="synthetic-photograph-002",
            is_synthetic=True,
            titles=(
                LocalizedValue("Photographie fictive d'une rue bruxelloise", "fr"),
                LocalizedValue("Fictional photograph of a Brussels street", "en"),
            ),
            descriptions=(
                LocalizedValue(
                    "Scène urbaine synthétique montrant des passants et un tramway."
                    " Aucun lieu ou événement réel n'est représenté.",
                    "fr",
                ),
            ),
            media_type=MediaType.IMAGE,
            object_type="Photograph",
            date_display="1946 (fictional)",
            providers=(
                ProviderRecord(
                    provider_id="synthetic-provider-photo",
                    name="Synthetic Brussels Photo Archive",
                    role=ProviderRole.DATA_PROVIDER,
                    homepage_url="https://example.org/lowlands-lens/photo-archive",
                ),
            ),
            source_links=(
                SourceLinkRecord(
                    kind=SourceLinkKind.RECORD,
                    label="Synthetic record page",
                    url="https://example.org/lowlands-lens/records/photo-002",
                ),
                SourceLinkRecord(
                    kind=SourceLinkKind.PROVIDER,
                    label="Synthetic provider page",
                    url="https://example.org/lowlands-lens/photo-archive",
                ),
            ),
            rights=(
                METADATA_RIGHTS,
                RightsRecord(
                    scope=RightsScope.DIGITAL_OBJECT,
                    status=RightsStatus.UNKNOWN,
                    label="Digital-object rights unknown",
                ),
            ),
        ),
        search_terms=(
            "photograph",
            "photographie",
            "photo",
            "brussels",
            "bruxelles",
            "street",
            "rue",
            "tram",
            "1946",
        ),
    ),
    SyntheticFixture(
        evidence=EvidenceRecord(
            evidence_id="synthetic-audio-003",
            is_synthetic=True,
            titles=(
                LocalizedValue("Fictief mondeling verhaal over havenwerk", "nl"),
                LocalizedValue("Fictional oral history about dock work", "en"),
            ),
            descriptions=(
                LocalizedValue(
                    "Een synthetische audiofiche over dagelijks werk in een "
                    "niet-bestaande Belgische haven.",
                    "nl",
                ),
            ),
            media_type=MediaType.SOUND,
            object_type="Oral history recording",
            date_display="1972 (fictional)",
            providers=(
                ProviderRecord(
                    provider_id="synthetic-provider-audio",
                    name="Synthetic Oral History Workshop",
                    role=ProviderRole.DATA_PROVIDER,
                    homepage_url="https://example.org/lowlands-lens/audio",
                ),
            ),
            source_links=(
                SourceLinkRecord(
                    kind=SourceLinkKind.RECORD,
                    label="Synthetic record page",
                    url="https://example.org/lowlands-lens/records/audio-003",
                ),
            ),
            rights=(
                METADATA_RIGHTS,
                RightsRecord(
                    scope=RightsScope.DIGITAL_OBJECT,
                    status=RightsStatus.KNOWN,
                    label="CC BY-NC 4.0 (synthetic fixture)",
                    uri="https://creativecommons.org/licenses/by-nc/4.0/",
                ),
            ),
        ),
        search_terms=(
            "audio",
            "oral history",
            "mondeling verhaal",
            "dock",
            "haven",
            "work",
            "werk",
            "1972",
        ),
    ),
)
