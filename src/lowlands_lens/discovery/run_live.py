"""Explicit command for one bounded, redacted Phase 3 live snapshot."""

import argparse
import json
from pathlib import Path
from typing import Final

from lowlands_lens.discovery.client import EuropeanaDiscoveryClient
from lowlands_lens.discovery.configuration import EuropeanaCredentials
from lowlands_lens.discovery.contracts import RecordRequestConfiguration
from lowlands_lens.discovery.exploration import run_query_matrix
from lowlands_lens.discovery.httpx2_transport import Httpx2Transport
from lowlands_lens.discovery.query_matrix import load_discovery_query_matrix

SAMPLE_QUERY_IDS: Final = (
    "places-en-001",
    "places-fr-001",
    "artists-en-001",
    "war-nl-001",
    "colonial-fr-001",
    "media-fr-001",
)


def _write_new_json(path: Path, value: object) -> None:
    """Write deterministic JSON without replacing prior snapshot evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
        stream.write("\n")


def main() -> None:
    """Run one sequential query matrix and bounded Record sample."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--snapshot-date", required=True)
    arguments = parser.parse_args()

    matrix = load_discovery_query_matrix(arguments.matrix)
    credentials = EuropeanaCredentials.from_environment()

    with Httpx2Transport() as transport:
        client = EuropeanaDiscoveryClient(transport, credentials)
        summaries = run_query_matrix(client, matrix)
        summary_by_id = {summary.query_id: summary for summary in summaries}

        query_documents = []
        for query, summary in zip(matrix.queries, summaries, strict=True):
            query_documents.append(
                {
                    "query_id": query.query_id,
                    "category": query.category.value,
                    "language": query.language.value,
                    "query_text": query.query_text,
                    "filters": list(query.filters),
                    "summary": summary.model_dump(mode="json"),
                }
            )

        _write_new_json(
            arguments.output_dir / "search_summary.json",
            {
                "snapshot_date": arguments.snapshot_date,
                "matrix_schema_version": matrix.schema_version,
                "matrix_purpose": matrix.purpose,
                "query_count": len(summaries),
                "queries": query_documents,
            },
        )

        sample_manifest = []
        records_directory = arguments.output_dir / "records"
        for sample_number, query_id in enumerate(SAMPLE_QUERY_IDS, start=1):
            summary = summary_by_id[query_id]
            if not summary.sampled_records:
                continue
            reference = summary.sampled_records[0]
            snapshot = client.record_snapshot(
                RecordRequestConfiguration(record_id=reference.record_id)
            )
            filename = f"record_{sample_number:02d}.json"
            serialized = json.dumps(snapshot.sanitized_document, ensure_ascii=False)
            if credentials.api_key in serialized:
                raise RuntimeError("Credential redaction failed; snapshot not written.")
            _write_new_json(
                records_directory / filename,
                snapshot.sanitized_document,
            )
            sample_manifest.append(
                {
                    "query_id": query_id,
                    "record_id": reference.record_id,
                    "rank": reference.rank,
                    "sampling_reason": reference.sampling_reason,
                    "local_raw_file": filename,
                }
            )

    _write_new_json(
        arguments.output_dir / "sample_manifest.json",
        {
            "snapshot_date": arguments.snapshot_date,
            "sample_count": len(sample_manifest),
            "samples": sample_manifest,
        },
    )
    print(f"queries_completed={len(summaries)}")
    print(f"record_samples_completed={len(sample_manifest)}")
    print(f"output_directory={arguments.output_dir}")


if __name__ == "__main__":
    main()
