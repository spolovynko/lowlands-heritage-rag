"""Framework-independent domain records used by application components."""

from dataclasses import dataclass
from enum import StrEnum


class Language(StrEnum):
    """Languages supported by the Phase 2 user journey."""

    ENGLISH = "en"
    FRENCH = "fr"
    DUTCH = "nl"


class MediaType(StrEnum):
    """Broad media category for a cultural-heritage object."""

    IMAGE = "image"
    TEXT = "text"
    SOUND = "sound"
    VIDEO = "video"
    THREE_D = "3d"


class ProviderRole(StrEnum):
    """Relationship between a provider and an evidence record."""

    PROVIDER = "provider"
    DATA_PROVIDER = "data_provider"


class SourceLinkKind(StrEnum):
    """Purpose of an evidence source link."""

    RECORD = "record"
    PROVIDER = "provider"
    DIGITAL_OBJECT = "digital_object"


class RightsScope(StrEnum):
    """Part of a record governed by a rights statement."""

    METADATA = "metadata"
    DIGITAL_OBJECT = "digital_object"


class RightsStatus(StrEnum):
    """Whether a usable rights statement is present."""

    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LocalizedValue:
    """Source text and its language tag, when known."""

    text: str
    language: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderRecord:
    """Provider attribution attached to an evidence record."""

    provider_id: str
    name: str
    role: ProviderRole
    homepage_url: str | None = None


@dataclass(frozen=True, slots=True)
class SourceLinkRecord:
    """Source-controlled link attached to an evidence record."""

    kind: SourceLinkKind
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class RightsRecord:
    """Attributed rights information for one record scope."""

    scope: RightsScope
    status: RightsStatus
    label: str
    uri: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """One immutable object-level evidence record."""

    evidence_id: str
    is_synthetic: bool
    titles: tuple[LocalizedValue, ...]
    descriptions: tuple[LocalizedValue, ...]
    media_type: MediaType
    object_type: str | None
    date_display: str | None
    providers: tuple[ProviderRecord, ...]
    source_links: tuple[SourceLinkRecord, ...]
    rights: tuple[RightsRecord, ...]
