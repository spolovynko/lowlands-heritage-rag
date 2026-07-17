"""Answer-generation port and framework-independent outcomes."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from lowlands_lens.domain import EvidenceRecord, Language


class AbstentionReason(StrEnum):
    """Reason a generator deliberately declines to answer."""

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNSUPPORTED_QUESTION = "unsupported_question"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


class GenerationUnavailableReason(StrEnum):
    """Reason answer generation cannot run."""

    NOT_CONFIGURED = "not_configured"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"


@dataclass(frozen=True, slots=True)
class GeneratedCitation:
    """Application-controlled reference to supplied evidence."""

    label: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    """Answer supported by citations to supplied evidence."""

    text: str
    citations: tuple[GeneratedCitation, ...]
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AbstainedAnswer:
    """Deliberate non-answer caused by an evidence limitation."""

    reason: AbstentionReason
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UnavailableAnswer:
    """Search-preserving result when generation cannot run."""

    reason: GenerationUnavailableReason
    limitations: tuple[str, ...]


type AnswerResult = GeneratedAnswer | AbstainedAnswer | UnavailableAnswer


class AnswerGenerator(Protocol):
    """Port implemented by deterministic and future model-backed generators."""

    def generate(
        self,
        question: str,
        language: Language,
        evidence: tuple[EvidenceRecord, ...],
    ) -> AnswerResult:
        """Create an answer outcome from an explicit evidence package."""
        ...
