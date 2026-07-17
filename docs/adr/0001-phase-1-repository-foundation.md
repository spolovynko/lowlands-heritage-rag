# ADR 0001: Phase 1 repository foundation

- Status: Accepted
- Date: 2026-07-16
- Scope: Phase 1 — Architecture decisions and repository foundation
- Supersedes: Individual Phase 1 ADRs 0001 through 0010

## Context

Lowlands Lens needed a small, reproducible Python foundation before data,
retrieval, model, or interface work. Phase 1 established packaging, dependency,
quality, configuration, infrastructure, migration, and CI boundaries without
adding application features.

The main drivers were deterministic installation, early quality enforcement,
safe local configuration, explicit service boundaries, reproducible schema
changes, and identical local and CI checks.

## Decision summary

| ID | Topic | Decision |
| --- | --- | --- |
| P1-D01 | Repository layout | One Python package under `src/` |
| P1-D02 | Python | Python `>=3.14,<3.15` |
| P1-D03 | Dependencies | uv 0.11.x with committed `uv.lock` |
| P1-D04 | Package identity | `lowlands-lens` / `lowlands_lens`, no Phase 1 CLI |
| P1-D05 | Build backend | `uv_build>=0.11.28,<0.12` |
| P1-D06 | Configuration | Environment variables, ignored `.env`, safe `.env.example` |
| P1-D07 | Quality | pytest, Ruff, and strict mypy |
| P1-D08 | Local database | PostgreSQL 18 and pgvector 0.8.5 in Compose |
| P1-D09 | Migrations | Alembic, SQLAlchemy Core, and Psycopg 3 |
| P1-D10 | CI | One GitHub Actions quality job |

## Decisions

### P1-D01, P1-D04, and P1-D05 — Package foundation

Use a single-package `src` layout. The distribution is `lowlands-lens`; the
import package is `lowlands_lens`. The repository remains
`lowlands-heritage-rag`. Phase 1 defines no CLI.

Use `uv_build>=0.11.28,<0.12` with its standard pure-Python layout. Root-level
modules, multiple packages, alternative product identities, and more flexible
build backends were rejected because the project does not yet need them.

### P1-D02 and P1-D03 — Runtime and dependency management

Use Python 3.14 and prevent accidental adoption of Python 3.15 with
`requires-python = ">=3.14,<3.15"`.

Use uv 0.11.x for dependency declaration, locking, synchronization, and command
execution. Commit `uv.lock`, ignore `.venv`, use dependency groups for
development tools, and require locked installation in local verification and
CI. pip requirements, Poetry, and PDM would introduce a different or overlapping
project workflow without a demonstrated benefit.

### P1-D06 — Configuration and secrets

Use environment variables for deployment-specific settings and secrets.
Application-owned names use the `LOWLANDS_LENS_` prefix; external tools may keep
their required names such as `POSTGRES_*`.

Ignore `.env` and `.env.*`, while committing only a non-secret `.env.example`.
Safe tool configuration belongs in tracked configuration files. No dedicated
settings package or secret service is introduced before a real consumer needs
one.

### P1-D07 — Tests and code quality

Use pytest for isolated unit tests, Ruff for linting and formatting, and mypy in
strict mode. The approved development ranges are:

- `pytest>=9.1,<10`
- `ruff>=0.15,<0.16`
- `mypy>=2.2,<3`

Checks cover `src/`, `tests/`, and migration Python code. Unit tests require no
network, credentials, containers, or database. Phase 1 adds no coverage target,
pre-commit framework, or task runner.

### P1-D08 — Docker Compose and PostgreSQL

Compose contains one persistent service named `db`, using
`pgvector/pgvector:0.8.5-pg18-bookworm`.

Bind PostgreSQL only to `127.0.0.1` on a configurable host port, use a named
volume mounted at `/var/lib/postgresql`, and report readiness with `pg_isready`.
Do not add application, migration, monitoring, or administration containers.
Normal stop/down operations retain the volume; deletion requires an explicit
destructive action.

### P1-D09 — Database migrations

Use Alembic with SQLAlchemy Core and Psycopg 3. This approves SQLAlchemy only as
the migration engine, not as an application ORM decision. Runtime ranges are:

- `alembic>=1.18.5,<1.19`
- `sqlalchemy>=2.0.51,<2.1`
- `psycopg[binary]>=3.3.4,<3.4`

Store configuration in `pyproject.toml` and environment-based connection logic
in `migrations/env.py`; do not retain `alembic.ini` or a tracked database URL.
Maintain one ordered revision history with explicit upgrades and downgrades.
The first revision owns `CREATE EXTENSION vector`; container initialization and
manual extension creation are not used.

### P1-D10 — Continuous integration

Use one GitHub Actions job on `ubuntu-latest` for pushes and pull requests. Use
Python from `.python-version`, uv 0.11.6, a locked installation, and read-only
repository permission.

CI verifies package import, pytest, Ruff linting, Ruff formatting, and strict
mypy. PostgreSQL and deployment are excluded from basic CI; their lifecycle and
migrations are validated by the separate local exit gate.

## Consequences

The repository has one installable package, one dependency workflow, one quality
toolchain, one local persistent service, one migration history, and one basic CI
job. These boundaries reduce accidental complexity and make later components
replaceable.

The costs are reliance on Python 3.14, uv-specific locking, several quality and
migration dependencies, a local Docker requirement for infrastructure checks,
and an Ubuntu-only initial CI job.

## Validation

Phase 1 passed its exit gate:

- Python 3.14.6 and uv 0.11.6 completed a clean locked installation.
- `lowlands_lens` imported successfully.
- pytest passed; Ruff linting and formatting passed; strict mypy passed.
- PostgreSQL 18.4 became healthy on the loopback-only port.
- Alembic revision `46feab49b164` upgraded, downgraded, and re-upgraded a fresh
  database volume.
- pgvector 0.8.5 was installed only through the migration.
- Infrastructure stopped with exit code 0.
- GitHub Actions CI run 1 passed in 21 seconds for commit `54db3a2`.
- No credentials, virtual environments, local data, or database files were
  committed.

## Reconsider when

Revisit the relevant decision when a required dependency cannot support the
approved Python/tool versions; components need independent releases; compiled
extensions or custom builds become necessary; configuration needs exceed simple
environment variables; quality tooling becomes inadequate; PostgreSQL/pgvector
cannot meet measured requirements; deployments cannot run Python migrations;
or platform/database CI failures justify broader automation.

## References

- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)
- [README](../../README.md)
- [uv documentation](https://docs.astral.sh/uv/)
- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [pgvector](https://github.com/pgvector/pgvector)
- [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/)
- [GitHub Actions run 1](https://github.com/spolovynko/lowlands-heritage-rag/actions/runs/29517125913)
