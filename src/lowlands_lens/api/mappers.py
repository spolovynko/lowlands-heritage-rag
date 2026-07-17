"""Mappings between framework-independent records and public API contracts."""

from pydantic import AnyHttpUrl

from lowlands_lens.api.contracts import (
    AbstainedResponse,
    AnsweredResponse,
    AnswerResponse,
    Citation,
    Evidence,
    GenerationUnavailableResponse,
    LocalizedText,
    MediaType,
    Provider,
    ProviderRole,
    RightsScope,
    RightsStatement,
    RightsStatus,
    SourceLink,
    SourceLinkKind,
    SupportedLanguage,
)
from lowlands_lens.api.contracts import (
    AbstentionReason as ContractAbstentionReason,
)
from lowlands_lens.api.contracts import (
    GenerationUnavailableReason as ContractUnavailableReason,
)
from lowlands_lens.application.answer_generation import (
    AbstainedAnswer,
    AnswerResult,
    GeneratedAnswer,
    UnavailableAnswer,
)
from lowlands_lens.domain import EvidenceRecord, Language


def to_contract_language(language: Language) -> SupportedLanguage:
    """Map an internal language value to the public contract."""
    return SupportedLanguage(language.value)


def to_evidence_contract(record: EvidenceRecord) -> Evidence:
    """Map one internal evidence record to its public representation."""
    return Evidence(
        evidence_id=record.evidence_id,
        is_synthetic=record.is_synthetic,
        titles=[
            LocalizedText(text=value.text, language=value.language)
            for value in record.titles
        ],
        descriptions=[
            LocalizedText(text=value.text, language=value.language)
            for value in record.descriptions
        ],
        media_type=MediaType(record.media_type.value),
        object_type=record.object_type,
        date_display=record.date_display,
        providers=[
            Provider(
                provider_id=provider.provider_id,
                name=provider.name,
                role=ProviderRole(provider.role.value),
                homepage_url=(
                    AnyHttpUrl(provider.homepage_url)
                    if provider.homepage_url is not None
                    else None
                ),
            )
            for provider in record.providers
        ],
        source_links=[
            SourceLink(
                kind=SourceLinkKind(link.kind.value),
                label=link.label,
                url=AnyHttpUrl(link.url),
            )
            for link in record.source_links
        ],
        rights=[
            RightsStatement(
                scope=RightsScope(statement.scope.value),
                status=RightsStatus(statement.status.value),
                label=statement.label,
                uri=(AnyHttpUrl(statement.uri) if statement.uri is not None else None),
            )
            for statement in record.rights
        ],
    )


def to_answer_contract(
    result: AnswerResult,
    *,
    question: str,
    language: Language,
) -> AnswerResponse:
    """Map one internal answer outcome to the discriminated public union."""
    contract_language = to_contract_language(language)
    if isinstance(result, GeneratedAnswer):
        return AnsweredResponse(
            question=question,
            language=contract_language,
            answer_text=result.text,
            citations=[
                Citation(
                    citation_id=f"citation-{index}",
                    label=citation.label,
                    evidence_ids=list(citation.evidence_ids),
                )
                for index, citation in enumerate(result.citations, start=1)
            ],
            limitations=list(result.limitations),
        )

    if isinstance(result, AbstainedAnswer):
        return AbstainedResponse(
            question=question,
            language=contract_language,
            reason=ContractAbstentionReason(result.reason.value),
            limitations=list(result.limitations),
        )

    if isinstance(result, UnavailableAnswer):
        return GenerationUnavailableResponse(
            question=question,
            language=contract_language,
            reason=ContractUnavailableReason(result.reason.value),
            limitations=list(result.limitations),
        )

    raise TypeError(f"Unsupported answer result: {type(result).__name__}")
