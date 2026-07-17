# Lowlands Lens

Lowlands Lens is a multilingual, evidence-grounded assistant for Belgian
cultural heritage from 1900 to the present.

Phase 2 provides a complete local API-first interface prototype using clearly
labelled deterministic synthetic records. It demonstrates search, evidence
selection, answers, citations, rights, empty results, structured errors,
abstention, and unavailable generation without Europeana access, credentials,
a production database, embeddings, prompts, or an answer model.

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

The tracked `.env.example` intentionally contains no working credentials.

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
|-- src/lowlands_lens/   # Domain, ports, adapters, API, and static interface
|-- tests/               # Contract, component, API, and interface tests
|-- compose.yaml         # Local persistent database boundary
|-- pyproject.toml       # Package, dependencies, and tool configuration
`-- uv.lock              # Exact dependency lock
```

Local credentials, virtual environments, database data, and root-level `data/`
content must remain untracked.
