"""Deterministic Phase 2 answer-generation adapter."""

from typing import Final

from lowlands_lens.application.answer_generation import (
    AbstainedAnswer,
    AbstentionReason,
    AnswerResult,
    GeneratedAnswer,
    GeneratedCitation,
    GenerationUnavailableReason,
    UnavailableAnswer,
)
from lowlands_lens.domain import EvidenceRecord, Language

SIMULATED_UNAVAILABLE_QUESTION: Final = "simulate-generation-unavailable"

_UNSUPPORTED_MARKERS: Final = (
    "objectively",
    "all belgians",
    "most influential",
    "greatest effect",
    "objectivement",
    "tous les belges",
    "objectief",
    "alle belgen",
)


class DeterministicAnswerGenerator:
    """Produce repeatable answers without a model, prompt, or credentials."""

    def generate(
        self,
        question: str,
        language: Language,
        evidence: tuple[EvidenceRecord, ...],
    ) -> AnswerResult:
        normalized_question = question.strip().casefold()

        if normalized_question == SIMULATED_UNAVAILABLE_QUESTION:
            return UnavailableAnswer(
                reason=GenerationUnavailableReason.NOT_CONFIGURED,
                limitations=(
                    self._message(
                        language,
                        en="No answer model is configured in Phase 2. Search results "
                        "remain available.",
                        fr="Aucun modèle de réponse n'est configuré en phase 2. Les "
                        "résultats de recherche restent disponibles.",
                        nl="In fase 2 is geen antwoordmodel geconfigureerd. De "
                        "zoekresultaten blijven beschikbaar.",
                    ),
                ),
            )

        if any(marker in normalized_question for marker in _UNSUPPORTED_MARKERS):
            return AbstainedAnswer(
                reason=AbstentionReason.UNSUPPORTED_QUESTION,
                limitations=(
                    self._message(
                        language,
                        en="The selected synthetic records cannot support an objective "
                        "or population-wide conclusion.",
                        fr="Les notices synthétiques sélectionnées ne permettent pas "
                        "une conclusion objective ou générale.",
                        nl="De geselecteerde synthetische records ondersteunen geen "
                        "objectieve of algemene conclusie.",
                    ),
                ),
            )

        if "conflict" in normalized_question or "contradic" in normalized_question:
            return AbstainedAnswer(
                reason=AbstentionReason.CONFLICTING_EVIDENCE,
                limitations=(
                    self._message(
                        language,
                        en="The question asks for conflict handling, so the deterministic "
                        "Phase 2 adapter demonstrates an abstention.",
                        fr="La question demande de traiter un conflit; l'adaptateur "
                        "déterministe montre donc une abstention.",
                        nl="De vraag vraagt om conflictafhandeling; daarom toont de "
                        "deterministische adapter een onthouding.",
                    ),
                ),
            )

        if not evidence:
            return AbstainedAnswer(
                reason=AbstentionReason.INSUFFICIENT_EVIDENCE,
                limitations=(
                    self._message(
                        language,
                        en="No evidence was supplied for this answer.",
                        fr="Aucune preuve n'a été fournie pour cette réponse.",
                        nl="Er is geen bewijsmateriaal voor dit antwoord aangeleverd.",
                    ),
                ),
            )

        citations = tuple(
            GeneratedCitation(
                label=f"[{index}] {self._preferred_title(record, language)}",
                evidence_ids=(record.evidence_id,),
            )
            for index, record in enumerate(evidence, start=1)
        )
        labels = ", ".join(citation.label for citation in citations)
        answer_text = self._message(
            language,
            en=f"The selected synthetic records include {labels}. They demonstrate "
            "the Phase 2 evidence and citation journey; they do not establish "
            "historical facts.",
            fr=f"Les notices synthétiques sélectionnées comprennent {labels}. Elles "
            "illustrent le parcours de preuves et de citations de la phase 2; elles "
            "n'établissent aucun fait historique.",
            nl=f"De geselecteerde synthetische records omvatten {labels}. Ze tonen "
            "het bewijs- en citatiepad van fase 2 en stellen geen historische "
            "feiten vast.",
        )
        return GeneratedAnswer(
            text=answer_text,
            citations=citations,
            limitations=(
                self._message(
                    language,
                    en="This deterministic answer uses synthetic development records only.",
                    fr="Cette réponse déterministe utilise uniquement des notices "
                    "synthétiques de développement.",
                    nl="Dit deterministische antwoord gebruikt alleen synthetische "
                    "ontwikkelrecords.",
                ),
            ),
        )

    @staticmethod
    def _preferred_title(record: EvidenceRecord, language: Language) -> str:
        for title in record.titles:
            if title.language == language.value:
                return title.text
        return record.titles[0].text

    @staticmethod
    def _message(language: Language, *, en: str, fr: str, nl: str) -> str:
        return {Language.ENGLISH: en, Language.FRENCH: fr, Language.DUTCH: nl}[language]
