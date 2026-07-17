"""Retrieval ports and result types."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from lowlands_lens.domain import EvidenceRecord, Language


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Framework-independent search input."""

    text: str
    language: Language
    limit: int


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Records returned by a retriever plus visible limitations."""

    records: tuple[EvidenceRecord, ...]
    total: int
    limitations: tuple[str, ...] = ()


class RetrievalUnavailableError(RuntimeError):
    """Raised when the retrieval dependency cannot serve a request."""


class Retriever(Protocol):
    """Port implemented by mock and future production retrievers."""

    def search(self, query: RetrievalQuery) -> RetrievalResult:
        """Return evidence matching a query."""
        ...


class EvidenceRepository(Protocol):
    """Port for resolving previously returned evidence identifiers."""

    def get_by_ids(self, evidence_ids: Sequence[str]) -> tuple[EvidenceRecord, ...]:
        """Return known records in the requested identifier order."""
        ...
