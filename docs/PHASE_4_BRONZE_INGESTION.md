# Phase 4 master record: Reliable Bronze ingestion

- Status: Implemented and verified within the approved test-only boundary
- Date: 2026-07-17
- Live validation: Not approved and not executed
- Media acquisition: Prohibited

## 1. Outcome

Phase 4 adds a restartable, idempotent, content-addressed Europeana Record
ingestion boundary. It reuses the Phase 3 client and transport instead of
duplicating authentication, validation, redaction, or HTTP behavior. The Phase
2 public API and deterministic mock adapters remain unchanged.

The approved first boundary is enforced in `RunConfiguration`:

- query ID `war-nl-001` only;
- at most 10 unique candidates;
- at most five Record source calls, including retries;
- at most 10 Search calls;
- fake/test sources only;
- output rooted at the configured Phase 4 directory;
- no media downloads.

The executable CLI supports safe validation but refuses network execution until
the exact Step 11 live budget receives separate approval.

## 2. Architecture

```text
approved query matrix
        |
        v
cursor pagination ---> EuropeanaSource protocol
        |                       ^
        |                       |
        |              EuropeanaDiscoveryClient
        v
IngestionOrchestrator
        |
        |-- BronzeObjectStore ---> immutable .json.gz objects
        |-- RunManifestStore  ---> atomic manifest.json
        |-- CheckpointStore   ---> atomic checkpoint.json
        |-- QuarantineStore   ---> immutable sanitized failures
        |-- Clock / Sleeper / JitterSource
        `-- ContentHasher     ---> SHA-256
```

`src/lowlands_lens/ingestion/` contains:

| Module | Responsibility |
| --- | --- |
| `contracts.py` | Bounds, run states, entries, failures, checkpoints, and impossible-state validation |
| `ports.py` | Small source, storage, state, time, retry, and hash protocols |
| `serialization.py` | Canonical JSON v1, deterministic gzip, and SHA-256 |
| `filesystem.py` | Immutable Bronze/quarantine publication and atomic manifest/checkpoint persistence |
| `pagination.py` | Cursor and candidate deduplication with bounded termination |
| `retry.py` | Sanitized failure classification and bounded backoff |
| `orchestrator.py` | Durable ordering, call reservation, resume, quarantine, and recovery |
| `composition.py` | Filesystem and runtime adapter wiring around an injected source |
| `cli.py` | Pre-access validation and safe summaries |

The existing `EuropeanaDiscoveryClient` structurally satisfies
`EuropeanaSource`; it does not inherit from or import the ingestion protocol.

## 3. Bronze identity and layout

The content hash is calculated over complete recursively redacted provider JSON
serialized as project canonical JSON v1:

- UTF-8;
- sorted object keys;
- compact separators;
- original array order;
- no ASCII escaping;
- no non-finite numbers;
- no trailing newline.

The uncompressed canonical bytes receive a lowercase SHA-256 digest. Storage
uses deterministic gzip with compression level 9 and modification time zero.
Compression does not influence content identity.

```text
data/phase4/
|-- bronze/europeana/records/<record-key>/sha256/<content-hash>.json.gz
`-- runs/<run-id>/
    |-- manifest.json
    |-- checkpoint.json
    `-- quarantine/<request-id>.json
```

`record-key` is a SHA-256 digest of the exact Europeana ID, preventing provider
identifiers from becoming unsafe path segments. Manifests retain the original
ID and an output-root-relative raw path.

## 4. Durable execution

For successful Records, the order is:

1. reserve the provider call in the manifest;
2. retrieve a sanitized Record snapshot;
3. publish or resolve the immutable raw object;
4. append the successful manifest entry;
5. advance the checkpoint.

For terminal failures, quarantine replaces raw-object publication. Search pages
persist safe candidate provenance before advancing their cursor checkpoint.

Temporary files are flushed and `fsync`ed. Immutable files are published by an
exclusive hard link that cannot replace an existing path. Mutable state is
flushed and atomically replaced. Existing raw objects are decompressed and
verified before being reported as already present.

## 5. Resume and recovery behavior

| Interruption point | Resume behavior |
| --- | --- |
| Before raw storage | Repeat the unfinished Record within remaining call budget |
| After raw storage, before manifest | Resolve identical raw object and create missing provenance |
| After manifest, before checkpoint | Advance the lagging checkpoint without another Record call |
| After terminal quarantine | Preserve failure history and reconcile its checkpoint |

A run can resume only with the exact persisted configuration and run ID.
Completed runs cannot be resumed. A new run may reference existing raw objects.

Selected retryable quarantine failures are retried in a new recovery run. Its
configuration names the source run and exact failure request IDs. Recovery does
not execute Search and cannot edit the source manifest or successful evidence.

## 6. Pagination, retries, and failure classes

Cursor traversal starts at `*`. Seen cursors and unique Record IDs are separate
sets. It stops on a missing cursor, repeated cursor, candidate ceiling, Search
ceiling, or approved stop condition.

Retryable:

- transport timeout or connection failure;
- HTTP 429, using numeric `Retry-After` when available;
- HTTP 5xx.

Permanent:

- authentication rejection;
- not found;
- invalid JSON or provider contract;
- Bronze integrity failure;
- other unclassified HTTP failures.

Backoff uses capped exponential delay with injected jitter. Attempts and total
delay are bounded. Each Record attempt is reserved durably before provider
access, so a crash cannot reset the five-call ceiling.

## 7. Security boundary

- Credentials exist only in the existing configuration/client boundary.
- Recursive redaction precedes canonicalization, hashing, and persistence.
- Provider payload model dumps are not used for Bronze because they discard
  unknown fields.
- Exceptions and quarantine records contain predefined sanitized messages.
- Quarantine excludes headers, URLs, query parameters, response bodies,
  validation input, and exception representations.
- The CLI accepts no credential argument and prints no raw metadata.
- Media links remain metadata; no component follows them.
- Ordinary tests use fake transports and sources.

An end-to-end test sends a recognizable fake secret through both the real
client's `X-Api-Key` header and provider `apikey` fields, then scans every stored
artifact and finds zero occurrences.

## 8. Safe operation

Validate the exact approved configuration without network access:

```powershell
uv run --locked lowlands-lens-ingest --matrix config/phase3/discovery_queries_v1.toml --query-id war-nl-001 --output-root data/phase4 --run-id example-validation --candidate-limit 10 --record-request-limit 5 --search-page-limit 10 --validate-only
```

Expected safe summary fields include status, run ID, query ID, limits, output
root, `live_requests=false`, and `media_downloads=false`.

Running the command without `--validate-only` currently fails before source
construction with a message that live execution is disabled. Do not bypass this
gate. Step 11 requires explicit approval of the exact Search-page and Record
budgets before adding the real source composition.

Run the focused credential-free suite:

```powershell
uv run --locked pytest tests/test_ingestion_contracts.py tests/test_bronze_storage.py tests/test_ingestion_pagination_retry.py tests/test_ingestion_e2e.py tests/test_ingestion_cli.py
```

Run all repository checks:

```powershell
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv build
```

## 9. Demonstrated exit evidence

- The focused Phase 4 suite passed 25 tests; the complete repository suite
  passed 96 tests without credentials or network access.
- Ruff lint and formatting passed across 55 files, strict mypy passed across
  all configured source/test/migration paths, and the source distribution and
  wheel built successfully.
- Wheel inspection found every ingestion module and the
  `lowlands-lens-ingest` console entry point.
- An identical second run created zero duplicate raw versions.
- Changed content for the same source ID created a new immutable version.
- Every raw path was referenced by a manifest entry with request ID, run ID,
  source ID, timestamp, and content hash.
- Interruptions before storage, after storage, and after manifest persistence
  resumed without loss or unsafe duplicate calls.
- Repeated cursors and duplicate records terminated safely.
- Retryable exhaustion and permanent failures were quarantined with sanitized
  context.
- Explicit retryable-failure recovery created a new run without changing the
  original manifest.
- Collision, corruption, and partial-write tests never overwrote evidence.
- Real-client fake-transport testing stored no injected secret.

## 10. Limitations and reconsideration triggers

- No live Europeana ingestion was approved or performed.
- Filesystem adapters assume one process and concurrency one.
- Whole manifests are atomically rewritten and are intended for bounded runs.
- Search response bodies are not retained; manifests retain safe Search and
  candidate provenance.
- Local output has no remote backup or retention policy.
- Provider limits and metadata may change before live validation.
- Large-scale needs should reconsider Dataset Download or OAI-PMH rather than
  indiscriminate Search traversal.
- Phase 5 normalization has not started.

## References

- [ADR 0004](adr/0004-phase-4-reliable-bronze-ingestion.md)
- [Phase 3 master record](adr/0003-phase-3-europeana-discovery-and-corpus-policy.md)
- [Implementation roadmap](IMPLEMENTATION_PHASES.md)
