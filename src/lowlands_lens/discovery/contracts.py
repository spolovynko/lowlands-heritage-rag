"""Typed contracts for bounded Phase 3 Europeana exploration."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyText = Annotated[str, Field(min_length=1)]
EuropeanaRecordId = Annotated[
    str,
    Field(pattern=r"^/[^/]+/.+$"),
]
MultilingualValues = dict[str, list[NonEmptyText]]


class ExplorationContractModel(BaseModel):
    """Base for strict project-controlled exploration data."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class EuropeanaPayloadModel(BaseModel):
    """Base for selected fields parsed from external Europeana JSON."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class SearchRequestConfiguration(ExplorationContractModel):
    """One bounded Search API request prepared from the query matrix."""

    query_id: NonEmptyText
    query: NonEmptyText = Field(max_length=500)
    refinements: tuple[NonEmptyText, ...] = Field(default_factory=tuple)
    facets: tuple[NonEmptyText, ...] = Field(min_length=1)
    profile: Literal["facets"] = "facets"
    rows: int = Field(default=12, ge=1, le=100)
    sample_limit: int = Field(default=6, ge=0, le=100)
    start: int | None = Field(default=None, ge=1)
    cursor: NonEmptyText | None = None

    @model_validator(mode="after")
    def validate_request_bounds(self) -> Self:
        """Reject contradictory, duplicate, or excessive requests."""
        if self.start is not None and self.cursor is not None:
            raise ValueError("start and cursor cannot be used together.")

        if self.start is not None:
            final_position = self.start + self.rows - 1
            if final_position > 1000:
                raise ValueError("Basic pagination cannot pass result 1000.")

        if self.sample_limit > self.rows:
            raise ValueError("sample_limit cannot exceed rows.")

        if len(set(self.refinements)) != len(self.refinements):
            raise ValueError("Search refinements must be unique.")

        if len(set(self.facets)) != len(self.facets):
            raise ValueError("Requested facets must be unique.")

        return self


class RecordRequestConfiguration(ExplorationContractModel):
    """One bounded request for a complete Europeana record."""

    record_id: EuropeanaRecordId


class EuropeanaFacetFieldPayload(EuropeanaPayloadModel):
    """One value and count returned inside a Europeana facet."""

    label: NonEmptyText
    count: int = Field(ge=0)


class EuropeanaFacetPayload(EuropeanaPayloadModel):
    """One raw facet group selected from a Search API response."""

    name: NonEmptyText
    fields: list[EuropeanaFacetFieldPayload] = Field(default_factory=list)


class EuropeanaSearchItemPayload(EuropeanaPayloadModel):
    """Selected discovery fields from one Search API item."""

    record_id: EuropeanaRecordId = Field(alias="id")
    titles: list[NonEmptyText] = Field(default_factory=list, alias="title")
    descriptions: list[NonEmptyText] = Field(
        default_factory=list,
        alias="dcDescription",
    )
    data_providers: list[NonEmptyText] = Field(
        default_factory=list,
        alias="dataProvider",
    )
    providers: list[NonEmptyText] = Field(default_factory=list, alias="provider")
    languages: list[NonEmptyText] = Field(default_factory=list, alias="language")
    countries: list[NonEmptyText] = Field(default_factory=list, alias="country")
    media_type: NonEmptyText | None = Field(default=None, alias="type")
    rights: list[NonEmptyText] = Field(default_factory=list)
    years: list[NonEmptyText] = Field(default_factory=list, alias="year")
    shown_at: NonEmptyText | None = Field(default=None, alias="edmIsShownAt")
    preview: NonEmptyText | None = Field(default=None, alias="edmPreview")


class EuropeanaSearchResponsePayload(EuropeanaPayloadModel):
    """Selected fields from one successful Search API response."""

    success: Literal[True]
    items_count: int = Field(alias="itemsCount", ge=0)
    total_results: int = Field(alias="totalResults", ge=0)
    next_cursor: NonEmptyText | None = Field(default=None, alias="nextCursor")
    items: list[EuropeanaSearchItemPayload] = Field(default_factory=list)
    facets: list[EuropeanaFacetPayload] = Field(default_factory=list)
    request_number: int | None = Field(
        default=None,
        alias="requestNumber",
        ge=0,
    )
    stats_duration: int | None = Field(
        default=None,
        alias="statsDuration",
        ge=0,
    )


class EuropeanaRecordProxyPayload(EuropeanaPayloadModel):
    """Selected multilingual descriptive fields from an EDM proxy."""

    about: NonEmptyText | None = None
    titles: MultilingualValues = Field(default_factory=dict, alias="dcTitle")
    descriptions: MultilingualValues = Field(
        default_factory=dict,
        alias="dcDescription",
    )
    dates: MultilingualValues = Field(default_factory=dict, alias="dcDate")
    subjects: MultilingualValues = Field(default_factory=dict, alias="dcSubject")
    creators: MultilingualValues = Field(default_factory=dict, alias="dcCreator")
    places: MultilingualValues = Field(
        default_factory=dict,
        alias="dctermsSpatial",
    )
    media_types: MultilingualValues = Field(
        default_factory=dict,
        alias="edmType",
    )
    rights: MultilingualValues = Field(default_factory=dict, alias="edmRights")


class EuropeanaWebResourcePayload(EuropeanaPayloadModel):
    """Selected source and rights fields for one digital resource."""

    about: NonEmptyText
    rights: MultilingualValues = Field(default_factory=dict, alias="edmRights")


class EuropeanaAggregationPayload(EuropeanaPayloadModel):
    """Selected provider, source-link, media, and rights fields."""

    about: NonEmptyText | None = None
    data_providers: MultilingualValues = Field(
        default_factory=dict,
        alias="edmDataProvider",
    )
    providers: MultilingualValues = Field(
        default_factory=dict,
        alias="edmProvider",
    )
    rights: MultilingualValues = Field(
        default_factory=dict,
        alias="edmRights",
    )
    shown_at: NonEmptyText | None = Field(default=None, alias="edmIsShownAt")
    shown_by: NonEmptyText | None = Field(default=None, alias="edmIsShownBy")
    preview: NonEmptyText | None = Field(default=None, alias="edmPreview")
    web_resources: list[EuropeanaWebResourcePayload] = Field(
        default_factory=list,
        alias="webResources",
    )


class EuropeanaRecordObjectPayload(EuropeanaPayloadModel):
    """Selected EDM structures from the Record API object."""

    about: NonEmptyText
    proxies: list[EuropeanaRecordProxyPayload] = Field(default_factory=list)
    aggregations: list[EuropeanaAggregationPayload] = Field(default_factory=list)


class EuropeanaRecordResponsePayload(EuropeanaPayloadModel):
    """Selected fields from one successful Record API response."""

    success: Literal[True]
    record_object: EuropeanaRecordObjectPayload = Field(alias="object")
    request_number: int | None = Field(
        default=None,
        alias="requestNumber",
        ge=0,
    )
    stats_duration: int | None = Field(
        default=None,
        alias="statsDuration",
        ge=0,
    )


class EuropeanaErrorPayload(EuropeanaPayloadModel):
    """Selected fields from a JSON error returned by Europeana."""

    success: Literal[False]
    error: NonEmptyText | None = None
    message: NonEmptyText | None = None

    @model_validator(mode="after")
    def require_error_information(self) -> Self:
        """Require at least one provider-supplied error description."""
        if self.error is None and self.message is None:
            raise ValueError("An error payload must contain error or message.")
        return self


class DiscoveryErrorCategory(StrEnum):
    """Stable failure categories used by Phase 3 exploration."""

    MISSING_CREDENTIALS = "missing_credentials"
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    HTTP_FAILURE = "http_failure"
    INVALID_JSON = "invalid_json"
    INVALID_RESPONSE = "invalid_response"


class DiscoveryError(ExplorationContractModel):
    """Sanitized failure information safe for reports and diagnostics."""

    category: DiscoveryErrorCategory
    message: NonEmptyText
    status_code: int | None = Field(default=None, ge=100, le=599)
    retry_after_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_retry_information(self) -> Self:
        """Keep retry guidance associated with rate limiting."""
        if (
            self.retry_after_seconds is not None
            and self.category is not DiscoveryErrorCategory.RATE_LIMITED
        ):
            raise ValueError("retry_after_seconds is valid only for rate limiting.")
        return self


class FacetValueCount(ExplorationContractModel):
    """One interpreted facet value and its returned count."""

    label: NonEmptyText
    count: int = Field(ge=0)


class FacetDistribution(ExplorationContractModel):
    """One facet distribution retained for Phase 3 analysis."""

    facet_name: NonEmptyText
    values: tuple[FacetValueCount, ...] = Field(default_factory=tuple)


class SampledRecordReference(ExplorationContractModel):
    """Traceable reason for selecting one record from a search result."""

    query_id: NonEmptyText
    record_id: EuropeanaRecordId
    rank: int = Field(ge=1)
    sampling_reason: NonEmptyText


class SearchExplorationSummary(ExplorationContractModel):
    """Bounded project-controlled summary of one discovery search."""

    query_id: NonEmptyText
    total_results: int = Field(ge=0)
    items_count: int = Field(ge=0)
    facets: tuple[FacetDistribution, ...] = Field(default_factory=tuple)
    sampled_records: tuple[SampledRecordReference, ...] = Field(default_factory=tuple)
    limitations: tuple[NonEmptyText, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_summary(self) -> Self:
        """Keep counts and references internally consistent."""
        if self.items_count > self.total_results:
            raise ValueError("items_count cannot exceed total_results.")

        facet_names = [facet.facet_name for facet in self.facets]
        if len(facet_names) != len(set(facet_names)):
            raise ValueError("Facet names must be unique within a summary.")

        record_ids = [reference.record_id for reference in self.sampled_records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("Sampled record IDs must be unique.")

        if any(
            reference.query_id != self.query_id for reference in self.sampled_records
        ):
            raise ValueError("Sampled records must reference the summary query ID.")

        return self
