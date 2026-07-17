from lowlands_lens.adapters.deterministic_answer_generation import (
    DeterministicAnswerGenerator,
)
from lowlands_lens.adapters.synthetic_records import SYNTHETIC_FIXTURES
from lowlands_lens.application.answer_generation import (
    AbstainedAnswer,
    AbstentionReason,
    GeneratedAnswer,
    GenerationUnavailableReason,
    UnavailableAnswer,
)
from lowlands_lens.domain import EvidenceRecord, Language


def selected_evidence() -> tuple[EvidenceRecord, ...]:
    return tuple(fixture.evidence for fixture in SYNTHETIC_FIXTURES[:2])


def test_generator_creates_citations_only_for_supplied_evidence() -> None:
    generator = DeterministicAnswerGenerator()

    result = generator.generate(
        question="What do these records demonstrate?",
        language=Language.ENGLISH,
        evidence=selected_evidence(),
    )

    assert isinstance(result, GeneratedAnswer)
    assert [citation.evidence_ids for citation in result.citations] == [
        ("synthetic-poster-001",),
        ("synthetic-photograph-002",),
    ]
    assert "do not establish historical facts" in result.text


def test_generator_uses_the_requested_answer_language() -> None:
    generator = DeterministicAnswerGenerator()

    result = generator.generate(
        question="Wat tonen deze records?",
        language=Language.DUTCH,
        evidence=selected_evidence(),
    )

    assert isinstance(result, GeneratedAnswer)
    assert result.text.startswith("De geselecteerde synthetische records")


def test_generator_abstains_from_unsupported_conclusions() -> None:
    generator = DeterministicAnswerGenerator()

    result = generator.generate(
        question="Who was objectively the most influential Belgian artist?",
        language=Language.ENGLISH,
        evidence=selected_evidence(),
    )

    assert isinstance(result, AbstainedAnswer)
    assert result.reason is AbstentionReason.UNSUPPORTED_QUESTION


def test_generator_abstains_without_evidence() -> None:
    generator = DeterministicAnswerGenerator()

    result = generator.generate(
        question="What does this show?",
        language=Language.ENGLISH,
        evidence=(),
    )

    assert isinstance(result, AbstainedAnswer)
    assert result.reason is AbstentionReason.INSUFFICIENT_EVIDENCE


def test_generator_preserves_search_when_generation_is_unavailable() -> None:
    generator = DeterministicAnswerGenerator()

    result = generator.generate(
        question="simulate-generation-unavailable",
        language=Language.ENGLISH,
        evidence=selected_evidence(),
    )

    assert isinstance(result, UnavailableAnswer)
    assert result.reason is GenerationUnavailableReason.NOT_CONFIGURED
    assert "Search results remain available" in result.limitations[0]
