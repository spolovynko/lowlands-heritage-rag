"""Version 1 public API contracts for Lowlands Lens."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

Identifier = Annotated[str, Field(min_length=1, max_length=200)]
NonEmptyText = Annotated[str, Field(min_length=1)]
LanguageTag = Annotated[str, Field(min_length=2, max_length=35)]


class ContractModel(BaseModel):
    """Base model for strict public API contracts."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class SupportedLanguage(StrEnum):
    """Languages supported for questions and answers."""

    ENGLISH = "en"
    FRENCH = "fr"
    DUTCH = "nl"


class LocalizedText(ContractModel):
    """Text with its source language when known."""

    text: NonEmptyText
    language: LanguageTag | None = None


class SourceLinkKind(StrEnum):
    """Purpose of a link associated with an evidence record."""

    RECORD = "record"
    PROVIDER = "provider"
    DIGITAL_OBJECT = "digital_object"


class SourceLink(ContractModel):
    """Validated link to a source or digital object."""

    kind: SourceLinkKind
    label: NonEmptyText
    url: AnyHttpUrl


class ProviderRole(StrEnum):
    """Relationship between a provider and an evidence record."""

    PROVIDER = "provider"
    DATA_PROVIDER = "data_provider"


class Provider(ContractModel):
    """Institution or aggregator attributed by a record."""

    provider_id: Identifier
    name: NonEmptyText
    role: ProviderRole
    homepage_url: AnyHttpUrl | None = None


class RightsScope(StrEnum):
    """Part of a record to which a rights statement applies."""

    METADATA = "metadata"
    DIGITAL_OBJECT = "digital_object"


class RightsStatus(StrEnum):
    """Whether a usable rights statement is present."""

    KNOWN = "known"
    UNKNOWN = "unknown"


class RightsStatement(ContractModel):
    """Attributed rights information without inferred permission."""

    scope: RightsScope
    status: RightsStatus
    label: NonEmptyText
    uri: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def validate_unknown_rights(self) -> Self:
        """Prevent unknown rights from carrying an authoritative URI."""
        if self.status is RightsStatus.UNKNOWN and self.uri is not None:
            raise ValueError("Unknown rights cannot include a rights URI.")
        return self


class MediaType(StrEnum):
    """Broad media category for an evidence record."""

    IMAGE = "image"
    TEXT = "text"
    SOUND = "sound"
    VIDEO = "video"
    THREE_D = "3d"


class Evidence(ContractModel):
    """One object-level cultural-heritage evidence record."""

    evidence_id: Identifier
    is_synthetic: bool
    titles: list[LocalizedText] = Field(min_length=1)
    descriptions: list[LocalizedText] = Field(default_factory=list)
    media_type: MediaType
    object_type: NonEmptyText | None = None
    date_display: NonEmptyText | None = None
    providers: list[Provider] = Field(min_length=1)
    source_links: list[SourceLink] = Field(min_length=1)
    rights: list[RightsStatement] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_rights_scopes(self) -> Self:
        """Require one statement for each distinct rights scope."""
        scopes = {statement.scope for statement in self.rights}
        required_scopes = {
            RightsScope.METADATA,
            RightsScope.DIGITAL_OBJECT,
        }
        if scopes != required_scopes:
            raise ValueError(
                "Evidence must contain one metadata and one digital-object "
                "rights statement."
            )
        return self


class SearchRequest(ContractModel):
    """Request for object-level evidence matching a query."""

    query: NonEmptyText = Field(max_length=500)
    language: SupportedLanguage
    limit: int = Field(default=10, ge=1, le=20)


class SearchOutcome(StrEnum):
    """Successful search outcomes."""

    RESULTS = "results"
    EMPTY = "empty"


class SearchResponse(ContractModel):
    """Successful search response, including a valid empty result."""

    outcome: SearchOutcome
    query: NonEmptyText
    language: SupportedLanguage
    results: list[Evidence]
    total: int = Field(ge=0)
    limitations: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        """Keep the outcome consistent with the returned evidence."""
        if self.outcome is SearchOutcome.EMPTY:
            if self.results:
                raise ValueError("An empty search cannot contain results.")
            if self.total != 0:
                raise ValueError("An empty search must have a total of zero.")

        if self.outcome is SearchOutcome.RESULTS and not self.results:
            raise ValueError("A results search must contain evidence.")

        if self.total < len(self.results):
            raise ValueError("Search total cannot be smaller than returned results.")

        return self


class Citation(ContractModel):
    """Application-controlled citation resolving to supplied evidence."""

    citation_id: Identifier
    label: NonEmptyText
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> Self:
        """Reject duplicate evidence references."""
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Citation evidence identifiers must be unique.")
        return self


class AnswerRequest(ContractModel):
    """Request for an answer based on previously returned evidence."""

    question: NonEmptyText = Field(max_length=500)
    language: SupportedLanguage
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> Self:
        """Reject duplicate selected evidence identifiers."""
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Answer evidence identifiers must be unique.")
        return self


class AnswerOutcome(StrEnum):
    """Possible successful answer-operation outcomes."""

    ANSWERED = "answered"
    ABSTAINED = "abstained"
    GENERATION_UNAVAILABLE = "generation_unavailable"


class AbstentionReason(StrEnum):
    """Reason the generator deliberately did not answer."""

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNSUPPORTED_QUESTION = "unsupported_question"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


class GenerationUnavailableReason(StrEnum):
    """Reason answer generation could not run."""

    NOT_CONFIGURED = "not_configured"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"


class AnswerResponseBase(ContractModel):
    """Fields shared by all successful answer-operation responses."""

    question: NonEmptyText
    language: SupportedLanguage


class AnsweredResponse(AnswerResponseBase):
    """Answer supported by one or more evidence citations."""

    outcome: Literal[AnswerOutcome.ANSWERED] = AnswerOutcome.ANSWERED
    answer_text: NonEmptyText
    citations: list[Citation] = Field(min_length=1)
    limitations: list[NonEmptyText] = Field(default_factory=list)


class AbstainedResponse(AnswerResponseBase):
    """Deliberate non-answer caused by insufficient evidence support."""

    outcome: Literal[AnswerOutcome.ABSTAINED] = AnswerOutcome.ABSTAINED
    answer_text: None = None
    citations: list[Citation] = Field(default_factory=list)
    reason: AbstentionReason
    limitations: list[NonEmptyText] = Field(min_length=1)


class GenerationUnavailableResponse(AnswerResponseBase):
    """Search-preserving response when generation cannot run."""

    outcome: Literal[AnswerOutcome.GENERATION_UNAVAILABLE] = (
        AnswerOutcome.GENERATION_UNAVAILABLE
    )
    answer_text: None = None
    citations: list[Citation] = Field(default_factory=list)
    reason: GenerationUnavailableReason
    limitations: list[NonEmptyText] = Field(min_length=1)


AnswerResponse = Annotated[
    AnsweredResponse | AbstainedResponse | GenerationUnavailableResponse,
    Field(discriminator="outcome"),
]


class HealthStatus(StrEnum):
    """Public liveness state for the local application."""

    OK = "ok"


class HealthResponse(ContractModel):
    """Liveness response that requires no external dependency."""

    status: Literal[HealthStatus.OK] = HealthStatus.OK
    contract_version: NonEmptyText


class ErrorCode(StrEnum):
    """Stable machine-readable operational error categories."""

    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    SEARCH_UNAVAILABLE = "search_unavailable"
    ANSWER_FAILED = "answer_failed"
    INTERNAL_ERROR = "internal_error"


class FieldError(ContractModel):
    """Validation problem associated with one request field."""

    field: NonEmptyText
    message: NonEmptyText


class ErrorDetail(ContractModel):
    """Machine-readable and user-readable operational error."""

    code: ErrorCode
    message: NonEmptyText
    field_errors: list[FieldError] = Field(default_factory=list)
    request_id: Identifier | None = None


class ErrorResponse(ContractModel):
    """Envelope for non-successful HTTP responses."""

    error: ErrorDetail
