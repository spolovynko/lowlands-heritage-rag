# ADR 0004: Reliable Bronze ingestion architecture

- Status: Accepted
- Date: 2026-07-17

## Context

Phase 4 must turn one explicitly bounded Europeana candidate source into
immutable, traceable Bronze evidence without changing the Phase 2 public API or
its mock adapters. The initial boundary permits at most 10 unique candidates
from `war-nl-001` and at most five Record requests. Work is test-only with fake
transports, local output is rooted at `data/phase4`, live requests require new
approval in Step 11, and media downloads are prohibited.

Phase 3 already provides credential-safe configuration, a synchronous transport
port, an HTTPX2 adapter, validated Search and Record contracts, cursor fields,
recursive response redaction, and a tested Europeana client. Phase 4 must reuse
those boundaries while adding content-addressed storage, durable provenance,
checkpoints, bounded retries, quarantine, and interruption recovery.

Europeana may echo the API credential inside a successful JSON response.
Therefore, unredacted response bytes cannot cross the persistence, hashing,
exception, or logging boundaries.

## Decision drivers

- Preserve the Phase 2 public API, application ports, and deterministic mock
  adapters.
- Reuse the Phase 3 Europeana client, transport port, credential boundary, and
  provider contracts instead of creating a second HTTP stack.
- Preserve complete source-shaped Record JSON while removing secrets before
  hashing or persistence.
- Make repeated ingestion idempotent and changed source content independently
  versioned without overwriting history.
- Make interruption recovery safe by ordering durable raw objects, manifest
  entries, and checkpoints explicitly.
- Trace every stored version to a bounded request and run without embedding
  mutable provenance in content identity.
- Keep provider access sequential, bounded, retry-budgeted, and testable without
  credentials, network access, or real sleeping.
- Quarantine terminal failures with useful sanitized context while protecting
  successful immutable history.
- Retain media references as metadata without downloading linked media.
- Keep Bronze capture separate from Phase 5 normalization, policy
  classification, translation, and duplicate clustering.

## Considered options

1. Reuse the Phase 3 client behind a dedicated ingestion orchestrator with
   small ports and local-filesystem adapters. This keeps provider access,
   durable storage, provenance, checkpoints, time, sleeping, and hashing
   independently testable. **Selected.**
2. Extend `discovery/run_live.py` into the ingestion pipeline. This would reuse
   a command that already writes snapshots, but it would mix Phase 3 reporting
   with pagination, retry, versioning, recovery, and operational state.
3. Build a separate Phase 4 Europeana client and one monolithic ingestion
   script. This appears locally simple, but it duplicates authentication,
   request construction, validation, redaction, and HTTP failure handling while
   making fault injection difficult.
4. Store Bronze responses directly in PostgreSQL. Transactions would help with
   metadata state, but database rows are a less transparent boundary for
   immutable compressed source evidence and would make ingestion depend on
   infrastructure that the bounded first implementation does not need.
5. Adopt cloud object storage and a workflow engine immediately. These tools
   can provide strong production capabilities, but they add deployment,
   credential, and operational complexity before local scale or concurrency
   demonstrates a need for them.

## Decision

### Component boundaries

Create a synchronous `lowlands_lens.ingestion` package beside, rather than
inside, the Phase 3 `discovery` package. Discovery remains responsible for
Europeana request construction, transport-independent response handling,
provider validation, and recursive redaction. Ingestion coordinates bounded
candidate collection, durable Record capture, retries, manifests, checkpoints,
and recovery.

The ingestion orchestrator will depend on these small protocols:

| Port | Responsibility | Production adapter |
| --- | --- | --- |
| `EuropeanaSource` | Search for candidates and retrieve sanitized Record snapshots | Existing `EuropeanaDiscoveryClient` |
| `BronzeObjectStore` | Canonicalize, hash, compress, and immutably store source documents | `FilesystemBronzeObjectStore` |
| `RunManifestStore` | Persist run configuration, status, counts, and request outcomes | `FilesystemRunManifestStore` |
| `CheckpointStore` | Load and atomically advance the last durable unit of work | `FilesystemCheckpointStore` |
| `QuarantineStore` | Publish immutable sanitized terminal failures | `FilesystemQuarantineStore` |
| `Clock` | Supply timezone-aware UTC timestamps | `SystemClock` |
| `Sleeper` | Apply retry delays | `BlockingSleeper` |
| `JitterSource` | Supply bounded retry jitter without test randomness | `RandomJitter` |
| `ContentHasher` | Produce content digests and permit collision fault tests | `Sha256Hasher` |

`BronzeObjectStore.store()` returns an immutable `StoredBronzeObject` value
containing the record ID, content hash, relative path, compressed size, and a
`StorageOutcome` of `created` or `already_present`. An enum is used instead of
a Boolean so callers cannot confuse existence, creation, and success.

The composition root is the only module that constructs concrete adapters. The
orchestrator receives protocols, and ordinary tests supply in-memory fakes,
fixed clocks, recording sleepers, and deterministic hashers. The existing
`HttpTransport` remains an internal dependency of `EuropeanaDiscoveryClient`;
ingestion does not introduce another HTTP abstraction.

The Phase 2 application ports, API contracts, and deterministic mock adapters
remain unchanged. Bronze ingestion is upstream data acquisition and does not
become a retrieval or answer-generation dependency in Phase 4.

### Bronze content identity and layout

The stored object is the complete sanitized provider JSON document, not a
Pydantic model dump or an envelope containing run metadata. Recursive redaction
is applied before serialization and hashing. Unknown provider fields and list
order are retained; no Unicode normalization, translation, date parsing,
rights classification, or duplicate clustering occurs.

Project canonical JSON version 1 uses UTF-8, sorted object keys, compact
separators, `ensure_ascii=False`, and rejection of non-finite numbers. It adds
no trailing newline. This makes insignificant source whitespace and object-key
order irrelevant while preserving JSON values and array order. The content ID
is the lowercase SHA-256 hexadecimal digest of these uncompressed canonical
bytes.

Raw objects use deterministic gzip with a fixed compression level, an empty
original filename, and modification time zero. The gzip representation is a
storage encoding only: hashes are calculated before compression so compressor
metadata or a future encoding migration cannot change source-content identity.

The initial local layout is:

```text
data/phase4/
|-- bronze/
|   `-- europeana/
|       `-- records/
|           `-- <record-key>/
|               `-- sha256/
|                   `-- <content-hash>.json.gz
`-- runs/
    `-- <run-id>/
        |-- manifest.json
        |-- checkpoint.json
        `-- quarantine/
            `-- <request-id>.json
```

`record-key` is the lowercase SHA-256 digest of the exact UTF-8 Europeana
record ID. This avoids path traversal, forbidden platform characters, and
unbounded path segments; the original record ID remains in the manifest.
`content-hash` is the canonical source-content digest. Manifests store paths
relative to `data/phase4` so moving the output root does not invalidate
provenance.

Raw objects are shared across runs. Run-specific configuration, timestamps,
request IDs, candidate rank and cursor, storage outcome, and quarantine state
remain under `runs/<run-id>`. Separating these trees prevents an identical
second run from creating another copy merely because its provenance changed.
The output root must be confirmed ignored before any separately approved live
validation.

### Durability and recovery

Immutable raw and quarantine files are first written to a uniquely named
temporary file in the destination directory. The adapter flushes and `fsync`s
the file, then publishes it with an exclusive same-filesystem operation that
cannot replace an existing final path. Temporary files are never referenced by
manifests and are removed after failed or interrupted publication attempts.

If an immutable content path already exists, the adapter decompresses it and
compares its canonical bytes with the new canonical bytes. Equal bytes produce
`already_present`. Invalid gzip, a digest mismatch, or different bytes at the
same digest path produce an integrity failure; existing evidence is never
replaced.

`manifest.json` is a complete, atomically replaced run document containing the
approved configuration, lifecycle status, counts, timestamps, and ordered
request entries. Completed entries are semantically immutable and keyed by
stable request IDs. `checkpoint.json` is a smaller atomically replaced replay
position containing collected candidate IDs, seen cursors, the next cursor,
Search completion state, and the next Record candidate index. Mutable files
are flushed before replacement.

Durable ordering is mandatory:

1. For a Record success, publish or resolve the raw object, persist the
   successful manifest entry, then advance the checkpoint.
2. For a terminal Record failure, publish the sanitized quarantine record,
   persist the failure manifest entry, then advance the checkpoint.
3. For a Search page, persist its safe request/candidate manifest entry, then
   advance the cursor checkpoint.

A checkpoint never advances for a retryable attempt that still has budget. On
resume, a terminal manifest entry with a checkpoint that lags is reconciled by
advancing the checkpoint without repeating the completed source call. If an
object was published but its manifest write was interrupted, replay resolves
the object as already present and safely creates the missing provenance.

Run states are `planned`, `running`, `completed`, `interrupted`, and `failed`.
Completed runs are not resumed or mutated. A planned or running state left by
a process crash, or an explicitly interrupted or failed run, may be resumed
only with the same persisted configuration and run ID. A new run may reference
existing raw versions but creates its own manifest and checkpoint.

### Pagination, retries, quarantine, and security

Cursor pagination begins with `*` and follows `nextCursor` sequentially. Seen
cursors and candidate record IDs are tracked independently. Iteration stops at
the first of: no next cursor, a repeated cursor, the candidate limit, the page
limit, or an approved stop condition. Duplicate records never consume another
unique-candidate slot.

Transport timeouts, connection failures, HTTP 429, and HTTP 5xx responses are
retryable. Authentication failures, not-found responses, invalid JSON, invalid
provider contracts, and local integrity failures are permanent. Numeric
`Retry-After` guidance is preferred; otherwise bounded exponential backoff with
jitter is used. Attempts and total delay are capped, and clock, sleeping, and
jitter are injected so tests neither wait nor depend on wall-clock time.

Every attempted Record source call consumes the run's Record-request ceiling,
including retries. A call reservation is persisted before access so a crash
cannot cause the approved ceiling to be exceeded on resume. Exhausting the run
ceiling produces a terminal sanitized outcome rather than another request.
Search pages and retry attempts have independent explicit limits.

Quarantine files contain only run ID, request ID, safe source record ID,
failure category, retryability, optional status and retry guidance, attempt
count, and timestamps. They contain no headers, URLs, query parameters,
response bodies, validation input, or exception representations. Recovery may
retry explicitly selected retryable failures but never edits completed history
or immutable raw objects.

The first implementation is synchronous with concurrency one. All ordinary
tests use fake sources and temporary directories. The CLI validates query,
limits, paths, and conflicting options before constructing network adapters.
It prints only statuses, counts, hashes, and sanitized paths. Search and Record
payloads may retain media URLs as metadata, but no Phase 4 component performs a
request to those URLs.

Selected retryable quarantine entries are recovered through a new bounded run.
The recovery configuration records the source run and explicit failure request
IDs. It bypasses Search, retrieves only those Record IDs, and gives the recovery
its own call budget, manifest, and checkpoint. The source manifest and all
previous successful evidence remain unchanged.

## Consequences

### Positive

- Identical source content is stored once while remaining traceable from many
  runs.
- Changed content creates a new version without altering prior evidence.
- Crash points between storage, manifests, and checkpoints are safe to replay.
- Provider, storage, clock, sleeper, jitter, and hash behavior can be fault
  tested without credentials, network access, or real waiting.
- Phase 3 request and redaction logic remains the single Europeana boundary.
- Source-shaped multilingual, rights, date, link, and unknown fields remain
  available to Phase 5.

### Negative

- Whole-document manifests are rewritten atomically after each state change;
  this is simple for the bounded first scale but unsuitable for very large
  manifests.
- Local hard-link publication assumes a filesystem that supports hard links
  within the output volume.
- Sequential execution favors safety and diagnosis over throughput.
- Search pages are represented by safe request and candidate provenance rather
  than stored as complete raw Search response bodies.

### Neutral

- Content identity is based on project canonical JSON v1, not raw HTTP bytes or
  an external canonical-JSON standard.
- Raw object paths use hashed record IDs; manifests provide the human-readable
  mapping.
- PostgreSQL, cloud object storage, workflow engines, media acquisition, and
  Silver normalization remain future decisions.

## Validation

- Contract tests reject unapproved queries and bounds, live requests, media
  downloads, naive timestamps, duplicate checkpoint state, and impossible
  manifest outcomes.
- Storage tests cover identical and changed content, deterministic gzip,
  forced hash collisions, corrupt existing objects, interrupted temporary
  writes, and atomic run-state round trips.
- Pagination tests cover duplicate records, repeated cursors, empty pages, no
  cursor, candidate bounds, and page bounds.
- Retry tests cover `Retry-After`, exponential delay, permanent failures,
  transient exhaustion, call reservation, and sanitized diagnostics.
- End-to-end tests cover identical reruns, changed versions, traceability,
  three interruption windows, resume without duplicate calls, quarantine,
  selected failure recovery, and recursive secret exclusion through the real
  Phase 3 client with a fake transport.
- CLI tests prove validation-only behavior, pre-access rejection, safe output,
  and complete injected-source execution.
- The focused Phase 4 suite passed 25 tests and the complete repository suite
  passed 96 tests. Ruff lint, Ruff formatting, strict mypy, package build, and
  wheel-content inspection passed.
- Ordinary tests use fake sources and temporary directories. Step 11 live
  validation remains separately gated and was not executed by this decision.

## Reconsider when

- A reviewed scale makes whole-manifest replacement or one-directory-per-record
  storage measurably inefficient.
- Multiple workers or hosts require coordination beyond concurrency one.
- Hard-link publication is unavailable on an approved target filesystem.
- Europeana bulk Dataset Download or OAI-PMH becomes preferable to bounded
  Search traversal.
- Retention policy, storage growth, or disaster recovery requires object
  storage or database-backed metadata.
- A new canonical serialization version is required; existing version-one
  hashes and files must remain readable.

## References

- [Phase 3 master record](0003-phase-3-europeana-discovery-and-corpus-policy.md)
- [Phase 4 master record](../PHASE_4_BRONZE_INGESTION.md)
- [Implementation roadmap](../IMPLEMENTATION_PHASES.md)
- [Phase 3 query matrix](../../config/phase3/discovery_queries_v1.toml)
