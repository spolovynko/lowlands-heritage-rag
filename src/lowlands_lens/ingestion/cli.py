"""Safe Phase 4 CLI with validation-only mode and injectable source access."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from lowlands_lens.discovery.exploration import request_from_query
from lowlands_lens.discovery.query_matrix import load_discovery_query_matrix
from lowlands_lens.ingestion.composition import compose_ingestion
from lowlands_lens.ingestion.contracts import RunConfiguration
from lowlands_lens.ingestion.filesystem import FilesystemRunManifestStore
from lowlands_lens.ingestion.ports import EuropeanaSource


class CliUsageError(ValueError):
    """Sanitized configuration error detected before source access."""


def build_parser() -> argparse.ArgumentParser:
    """Create the explicit bounded Phase 4 argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--query-id", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidate-limit", required=True, type=int)
    parser.add_argument("--record-request-limit", required=True, type=int)
    parser.add_argument("--search-page-limit", required=True, type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--recover-from-run")
    parser.add_argument("--recover-request-id", action="append", default=[])
    parser.add_argument("--validate-only", action="store_true")
    return parser


def run_cli(
    arguments: Sequence[str],
    *,
    source: EuropeanaSource | None = None,
) -> int:
    """Validate options and optionally execute with an explicitly injected source."""
    parsed = build_parser().parse_args(arguments)
    matrix_path = parsed.matrix
    output_root = parsed.output_root
    if output_root.exists() and not output_root.is_dir():
        raise CliUsageError("The output root exists and is not a directory.")
    if output_root.name in {"", ".", ".."}:
        raise CliUsageError("The output root must name a dedicated directory.")
    if parsed.resume and parsed.recover_from_run is not None:
        raise CliUsageError("Resume and failure recovery cannot be combined.")

    try:
        matrix = load_discovery_query_matrix(matrix_path)
    except OSError, ValueError:
        raise CliUsageError("The query matrix is missing or invalid.") from None
    selected = next(
        (query for query in matrix.queries if query.query_id == parsed.query_id),
        None,
    )
    if selected is None:
        raise CliUsageError("The selected query ID is not present in the matrix.")
    if selected.query_id != "war-nl-001":
        raise CliUsageError("The selected query is outside the approved Phase 4 scope.")

    try:
        configuration = RunConfiguration(
            run_id=parsed.run_id,
            query_id="war-nl-001",
            candidate_limit=parsed.candidate_limit,
            record_request_limit=parsed.record_request_limit,
            search_page_limit=parsed.search_page_limit,
            output_root=str(output_root),
            recovery_of_run_id=parsed.recover_from_run,
            selected_failure_request_ids=tuple(parsed.recover_request_id),
        )
    except ValidationError:
        raise CliUsageError(
            "The run configuration exceeds the approved scope."
        ) from None

    request = request_from_query(selected)
    if parsed.validate_only:
        _print_configuration(configuration, status="validated")
        return 0
    if source is None:
        raise CliUsageError(
            "Live execution is disabled until the Step 11 budget is approved."
        )

    runner = compose_ingestion(output_root, source)
    if configuration.recovery_of_run_id is None:
        manifest = runner.execute(configuration, request, resume=parsed.resume)
    else:
        source_manifest = FilesystemRunManifestStore(output_root).load(
            configuration.recovery_of_run_id
        )
        manifest = runner.execute_recovery(configuration, source_manifest)
    print(f"status={manifest.status.value}")
    print(f"run_id={configuration.run_id}")
    print(f"candidate_count={manifest.candidate_count}")
    print(f"record_request_count={manifest.record_request_count}")
    print(f"created_count={manifest.created_count}")
    print(f"existing_count={manifest.existing_count}")
    print(f"quarantined_count={manifest.quarantined_count}")
    print(f"output_root={configuration.output_root}")
    return 0


def _print_configuration(configuration: RunConfiguration, *, status: str) -> None:
    """Print only approved, secret-free configuration fields."""
    print(f"status={status}")
    print(f"run_id={configuration.run_id}")
    print(f"query_id={configuration.query_id}")
    print(f"candidate_limit={configuration.candidate_limit}")
    print(f"record_request_limit={configuration.record_request_limit}")
    print(f"search_page_limit={configuration.search_page_limit}")
    print(f"output_root={configuration.output_root}")
    print("live_requests=false")
    print("media_downloads=false")


def main() -> None:
    """Run validation safely; live composition remains deliberately unavailable."""
    try:
        exit_code = run_cli(sys.argv[1:])
    except CliUsageError as error:
        print(f"error={error}", file=sys.stderr)
        raise SystemExit(2) from None
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
