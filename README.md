# Lowlands Lens

Lowlands Lens is a multilingual, evidence-grounded assistant for Belgian
cultural heritage from 1900 to the present.

Phase 2 provides a complete local API-first interface prototype using clearly
labelled deterministic synthetic records. It demonstrates search, evidence
selection, answers, citations, rights, empty results, structured errors,
abstention, and unavailable generation without Europeana access, credentials,
a production database, embeddings, prompts, or an answer model.

Phase 3 adds a separate, bounded Europeana discovery boundary: secure
header-based credentials, typed Search and Record contracts, a versioned
English/French/Dutch query matrix, a dependency-inverted HTTP client,
credential-free tests, a dated coverage report, redacted local Record samples,
and an accepted corpus-selection policy. It does not replace the Phase 2 mock
retrieval adapter or connect live Europeana data to the public application.

Phase 4 adds credential-free, restartable Bronze ingestion with cursor
pagination, bounded retries, deterministic compressed raw storage, SHA-256
versioning, atomic manifests and checkpoints, quarantine, and selected-failure
recovery. Its executable CLI currently validates the approved test-only scope
and refuses live access pending the separate Step 11 gate.

## Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/) 0.11.x
- Docker with the `docker compose` command

The approved versions and boundaries are documented in `docs/adr/`.

## Install the locked environment

From the repository root:

```powershell
uv sync --locked
```

This creates `.venv`, installs the project in editable mode, and installs the
locked development tools. `.venv` is ignored by Git.

Verify the package import:

```powershell
uv run --locked python -c "import lowlands_lens"
```

## Run the Phase 2 application

Start the API and interface from the repository root:

```powershell
uv run --locked uvicorn lowlands_lens.api.app:app --host 127.0.0.1 --port 8000
```

Open the local interface at <http://127.0.0.1:8000/>. The generated OpenAPI
documentation is available at <http://127.0.0.1:8000/docs> and liveness at
<http://127.0.0.1:8000/api/v1/health>.

Try these deterministic searches:

- `poster` returns a synthetic result.
- `no matching object` returns a valid empty search.
- `simulate-search-error` demonstrates a structured operational error.

After selecting evidence, try a normal question, an unsupported subjective
question, or `simulate-generation-unavailable`. Search evidence remains visible
for every answer outcome.

The application does not require PostgreSQL or `.env` during Phase 2. See the
[Phase 2 user journey](docs/PHASE_2_USER_JOURNEY.md) for the complete walkthrough
and API examples.

## Local configuration

Create an ignored local configuration file:

```powershell
Copy-Item -LiteralPath .\.env.example -Destination .\.env
```

Edit `.env` locally:

- `POSTGRES_DB` is the local database name.
- `POSTGRES_USER` is the local database user.
- `POSTGRES_PASSWORD` is a unique local-only password. Never commit or paste it
  into logs, issues, or documentation.
- `POSTGRES_HOST` remains `127.0.0.1` for the approved local boundary.
- `POSTGRES_PORT` is the loopback host port. Use `5432` unless another local
  PostgreSQL process already occupies it; choose another unused port such as
  `5433` when necessary.
- `LOWLANDS_LENS_EUROPEANA_API_KEY` is the Phase 3 personal Europeana API key.
  Keep its real value only in the ignored `.env`; never place it in a URL,
  source file, test fixture, log, report, issue, or chat.

The tracked `.env.example` intentionally contains no working credentials.

Europeana discovery will load the application-owned variable through an
explicit configuration boundary and send it through the preferred `X-Api-Key`
header. The deprecated `wskey` query parameter is not supported. See the
[Phase 3 master record](docs/adr/0003-phase-3-europeana-discovery-and-corpus-policy.md)
for the essential API and credential-handling decisions.

Live validation found that Europeana echoes the actual header credential in a
successful JSON field named `apikey`. Never print or store an unredacted raw
response. The project live runner recursively redacts credential fields before
writing ignored local samples.

## Phase 3 discovery

The single source of truth is the
[Phase 3 master record](docs/adr/0003-phase-3-europeana-discovery-and-corpus-policy.md).
It combines the architecture decision, API boundary, live evidence, accepted
corpus policy, operating commands, limitations, and approval record.

The query matrix and aggregate observation artifact are tracked under
`config/phase3/`. Complete redacted Record samples remain under ignored
`data/phase3/`.

Ordinary tests and CI use no credential and make no Europeana request. After
explicitly approving a bounded live snapshot, run:

```powershell
uv run --locked --env-file .env python -m lowlands_lens.discovery.run_live --matrix config/phase3/discovery_queries_v1.toml --output-dir data/phase3/YYYY-MM-DD --snapshot-date YYYY-MM-DD
```

The command runs sequentially, does not retry or traverse cursors, refuses to
replace existing snapshot files, downloads no media, and prints no raw
metadata or credential.

## Phase 4 Bronze ingestion

Architecture, storage layout, recovery behavior, operations, evidence, and
limitations are recorded in the
[Phase 4 master record](docs/PHASE_4_BRONZE_INGESTION.md) and
[ADR 0004](docs/adr/0004-phase-4-reliable-bronze-ingestion.md).

Validate the approved test-only boundary without credentials or network access:

```powershell
uv run --locked lowlands-lens-ingest --matrix config/phase3/discovery_queries_v1.toml --query-id war-nl-001 --output-root data/phase4 --run-id example-validation --candidate-limit 10 --record-request-limit 5 --search-page-limit 10 --validate-only
```

The safe summary reports only identifiers, limits, status, and paths. Running
without `--validate-only` is deliberately disabled until the exact Step 11 live
budget is explicitly approved. No Phase 4 component downloads linked media.

Run the focused Phase 4 tests:

```powershell
uv run --locked pytest tests/test_ingestion_contracts.py tests/test_bronze_storage.py tests/test_ingestion_pagination_retry.py tests/test_ingestion_e2e.py tests/test_ingestion_cli.py
```

Validate Compose interpolation without displaying resolved secrets:

```powershell
docker compose config --quiet
```

## Local database

Start PostgreSQL and wait for its health check:

```powershell
docker compose up --detach --wait db
```

Inspect readiness:

```powershell
docker compose ps
```

Stop the service while preserving its container and named data volume:

```powershell
docker compose stop db
```

`docker compose down` removes the container and network but retains the named
volume. `docker compose down --volumes` also deletes the local database and must
be treated as a destructive reset.

## Database migrations

Migrations live in `migrations/`. Alembic source configuration is stored in
`pyproject.toml`; connection settings come from environment variables loaded by
uv from the ignored `.env` file.

With the database healthy, upgrade to the current revision:

```powershell
uv run --locked --env-file .env alembic upgrade head
```

Show the applied revision:

```powershell
uv run --locked --env-file .env alembic current
```

Downgrade all Phase 1 migrations:

```powershell
uv run --locked --env-file .env alembic downgrade base
```

The first revision owns the PostgreSQL `vector` extension. Do not enable the
extension manually or through Compose initialization scripts.

## Quality checks

Run unit tests:

```powershell
uv run --locked pytest
```

Run linting:

```powershell
uv run --locked ruff check .
```

Check formatting without changing files:

```powershell
uv run --locked ruff format --check .
```

Run strict static type checking:

```powershell
uv run --locked mypy
```

Build the package and verify that the interface assets are included:

```powershell
uv build
```

GitHub Actions runs the locked installation, package build, import check, tests,
linting, formatting check, and mypy on pushes and pull requests.

## Repository structure

```text
.
|-- .github/workflows/   # Continuous integration
|-- docs/                # Design, ADRs, and the Phase 2 user journey
|-- migrations/          # Alembic environment and revisions
|-- src/lowlands_lens/   # Domain, discovery, ingestion, API, and adapters
|-- tests/               # Contract, component, API, and interface tests
|-- compose.yaml         # Local persistent database boundary
|-- pyproject.toml       # Package, dependencies, and tool configuration
`-- uv.lock              # Exact dependency lock
```

Local credentials, virtual environments, database data, and root-level `data/`
content must remain untracked.
