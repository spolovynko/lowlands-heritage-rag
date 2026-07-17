"""Safe CLI configuration and injected-source execution tests."""

from pathlib import Path

import pytest

from lowlands_lens.discovery.client import EuropeanaRecordSnapshot
from lowlands_lens.discovery.contracts import (
    EuropeanaRecordResponsePayload,
    EuropeanaSearchResponsePayload,
    RecordRequestConfiguration,
    SearchRequestConfiguration,
)
from lowlands_lens.ingestion.cli import CliUsageError, run_cli

MATRIX_PATH = (
    Path(__file__).parents[1] / "config" / "phase3" / "discovery_queries_v1.toml"
)


class OneRecordSource:
    """Complete one injected CLI run without network access."""

    def __init__(self) -> None:
        self.search_count = 0
        self.record_count = 0

    def search(
        self,
        request: SearchRequestConfiguration,
    ) -> EuropeanaSearchResponsePayload:
        self.search_count += 1
        assert request.cursor == "*"
        return EuropeanaSearchResponsePayload.model_validate(
            {
                "success": True,
                "itemsCount": 1,
                "totalResults": 1,
                "items": [{"id": "/dataset/one"}],
            }
        )

    def record_snapshot(
        self,
        request: RecordRequestConfiguration,
    ) -> EuropeanaRecordSnapshot:
        self.record_count += 1
        document: dict[str, object] = {
            "success": True,
            "object": {
                "about": request.record_id,
                "proxies": [],
                "aggregations": [],
            },
        }
        return EuropeanaRecordSnapshot(
            parsed=EuropeanaRecordResponsePayload.model_validate(document),
            sanitized_document=document,
        )


def arguments(output_root: Path, **updates: str) -> list[str]:
    """Build one approved CLI argument list."""
    values = {
        "matrix": str(MATRIX_PATH),
        "query-id": "war-nl-001",
        "output-root": str(output_root),
        "run-id": "cli-run-001",
        "candidate-limit": "1",
        "record-request-limit": "1",
        "search-page-limit": "1",
    }
    values.update(updates)
    result: list[str] = []
    for name, value in values.items():
        result.extend((f"--{name}", value))
    return result


def test_validate_only_prints_safe_bounds_without_creating_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_root = tmp_path / "phase4"

    assert run_cli([*arguments(output_root), "--validate-only"]) == 0

    captured = capsys.readouterr()
    assert "status=validated" in captured.out
    assert "query_id=war-nl-001" in captured.out
    assert "live_requests=false" in captured.out
    assert "media_downloads=false" in captured.out
    assert not output_root.exists()


def test_cli_rejects_invalid_scope_and_unapproved_execution(tmp_path: Path) -> None:
    with pytest.raises(CliUsageError, match="approved scope"):
        run_cli(arguments(tmp_path / "bad", **{"candidate-limit": "11"}))

    with pytest.raises(CliUsageError, match="Live execution is disabled"):
        run_cli(arguments(tmp_path / "no-live"))


def test_cli_executes_complete_bounded_run_with_injected_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_root = tmp_path / "phase4"
    source = OneRecordSource()

    assert run_cli(arguments(output_root), source=source) == 0

    captured = capsys.readouterr()
    assert "status=completed" in captured.out
    assert "created_count=1" in captured.out
    assert "quarantined_count=0" in captured.out
    assert source.search_count == 1
    assert source.record_count == 1
    assert len(list((output_root / "bronze").rglob("*.json.gz"))) == 1
