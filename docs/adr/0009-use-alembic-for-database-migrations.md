# ADR 0009: Use Alembic for database migrations

- Status: Accepted
- Date: 2026-07-16

## Context

Phase 1 requires a reproducible database migration convention before application
tables or data-processing features are introduced.

The local database boundary uses PostgreSQL 18 with pgvector 0.8.5. The vector
extension must be enabled through a versioned migration rather than through a
container initialization script or a manual database command.

Database credentials must remain outside committed files. The migration
foundation must work with Python 3.14, the uv-managed environment, and the
existing environment-variable configuration convention.

## Decision drivers

- Reproducible schema changes on a clean PostgreSQL database
- Versioned and reviewable migration history
- Reliable upgrade and downgrade execution
- Compatibility with Python 3.14 and PostgreSQL 18
- No credentials in committed configuration
- Minimal custom migration infrastructure
- A clear boundary between Phase 1 infrastructure and later application schema

## Considered options

1. Alembic with SQLAlchemy Core and Psycopg 3
2. Raw SQL files with a custom migration runner and revision tracker
3. An external migration tool such as Flyway

## Decision

Use Alembic as the database migration and revision-management tool.

Use SQLAlchemy Core as Alembic's database engine layer and Psycopg 3 as the
PostgreSQL driver. This decision does not approve an ORM or determine the later
application persistence architecture.

Add the migration stack as bounded runtime dependencies:

- `alembic>=1.18.5,<1.19`
- `sqlalchemy>=2.0.51,<2.1`
- `psycopg[binary]>=3.3.4,<3.4`

Store the migration environment under the repository-root `migrations/`
directory. Maintain one ordered revision history. Commit every migration
revision and give each revision explicit `upgrade()` and `downgrade()`
operations.

Build the database connection from environment variables at runtime. Do not
store a database URL, username, password, or other credential in Alembic
configuration files.

The first migration will manage the PostgreSQL `vector` extension. Phase 1 will
not introduce application tables, ingestion structures, retrieval structures,
embeddings, or other Phase 2 features.

## Consequences

### Positive

- A clean database can be upgraded reproducibly to the current revision.
- Applied revisions are tracked by Alembic.
- Migration changes are visible in code review.
- PostgreSQL schema operations can run transactionally where PostgreSQL
  supports them.
- No custom revision tracker or migration runner is required.
- The same locked Python environment can run application checks and migrations.

### Negative

- Alembic, SQLAlchemy, and Psycopg become runtime dependencies.
- The repository gains migration configuration and generated support files.
- Migration authors must review generated operations rather than trusting
  automatic generation without inspection.
- The Psycopg binary distribution bundles its PostgreSQL client library.

### Neutral

- SQLAlchemy is initially limited to supporting migrations.
- The project may introduce SQLAlchemy metadata later, but that requires the
  relevant phase and does not follow automatically from this decision.
- Downgrades must be written explicitly and may not always be lossless once
  migrations contain production data transformations.

## Validation

- Install the locked dependencies in a clean environment.
- Run all migrations against the approved local PostgreSQL service.
- Confirm that Alembic records the current revision.
- Confirm that pgvector 0.8.5 becomes installed through the first migration.
- Downgrade to the base revision and upgrade to the latest revision again.
- Confirm that no database credential appears in a tracked file.

## Reconsider when

- The project must manage multiple independent databases or revision histories.
- Deployment can no longer run Python-based migration tooling.
- Psycopg binary packages become incompatible with the target environment.
- Measured operational requirements justify a separate migration system.

## References

- [Implementation phases](../IMPLEMENTATION_PHASES.md)
- [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/)
- [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/)
- [Psycopg documentation](https://www.psycopg.org/psycopg3/)