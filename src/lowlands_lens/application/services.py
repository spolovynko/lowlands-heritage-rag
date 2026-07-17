"""Application service dependencies supplied to the API adapter."""

from dataclasses import dataclass

from lowlands_lens.application.answer_generation import AnswerGenerator
from lowlands_lens.application.retrieval import EvidenceRepository, Retriever


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    """Small dependency container used by the application factory."""

    retriever: Retriever
    evidence_repository: EvidenceRepository
    answer_generator: AnswerGenerator
