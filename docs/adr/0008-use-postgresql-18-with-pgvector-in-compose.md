# ADR 0008: Use PostgreSQL 18 with pgvector in Compose

- Status: Accepted
- Date: 2026-07-16

## Context

The solution design identifies PostgreSQL as the serving system of record and pgvector as the future vector-search extension. These choices were provisional until a Phase 1 architecture decision established their local service boundary.

Phase 1 requires persistent local infrastructure that starts, reports readiness, and stops predictably. It does not require application containers, retrieval indexes, embeddings, ingestion, or production database schemas.

PostgreSQL 18 changed the official container storage layout. Its persistent volume boundary is `/var/lib/postgresql`, while its internal versioned data directory is created below that path.

## Decision drivers

- Provide one reproducible local relational database service.
- Make pgvector binaries available without maintaining a custom image.
- Preserve database data across normal container recreation.
- Bind database access only to the local host.
- Distinguish container liveness from database readiness.
- Keep credentials outside version control.
- Keep schema and extension creation reproducible through migrations.
- Avoid application and monitoring services before their phases begin.
- Make service start and stop behavior explicit.

## Considered options

1. Build a custom PostgreSQL image and compile pgvector.
2. Use the pgvector project’s PostgreSQL image.
3. Add application and migration containers during Phase 1.
4. Use a separate vector database service.

## Decision

Define one Docker Compose service named `db`.

Use this image:

`pgvector/pgvector:0.8.5-pg18-bookworm`

Use PostgreSQL major version 18 and pgvector version 0.8.5.

Bind the container’s PostgreSQL port to a configurable host port on `127.0.0.1` only. The default host port will be `5432`.

Persist database files in a Compose named volume mounted at:

`/var/lib/postgresql`

Require database name, user, and password through ignored local environment configuration. Do not commit working credentials or provide a working password default.

Use `pg_isready` as the service health check. Readiness must be evaluated separately from whether the container process is running.

Do not configure an automatic restart policy. Service lifecycle remains explicit through Docker Compose commands.

Compose will not run the Python application, migrations, ingestion, retrieval, monitoring, or administration tools during Phase 1.

The image makes the pgvector extension available, but it will not enable the extension through container initialization scripts. The migration history will own `CREATE EXTENSION vector`.

Normal service shutdown and `docker compose down` will retain the named volume. Volume deletion is a separate destructive operation and must never be part of the routine stop command.

## Consequences

### Positive

- PostgreSQL and pgvector are available through one maintained image.
- Local data survives normal container recreation.
- Database access is not exposed beyond the local host.
- Health checks provide a readiness signal.
- Schema state remains reproducible through migrations.
- Compose remains limited to persistent infrastructure.

### Negative

- The project depends on the pgvector project’s image publication.
- PostgreSQL major upgrades require a planned data migration.
- Developers must create local environment values before starting the service.
- A named volume consumes local disk until explicitly removed.

### Neutral

- PostgreSQL minor updates may arrive through refreshed image builds for the selected tag.
- The pgvector extension is available before it is enabled.
- Application processes run outside Compose during the current phase.

## Validation

- `docker compose config` validates the Compose model without exposing secrets.
- The database service starts independently.
- The health check transitions to healthy.
- PostgreSQL reports major version 18.
- The available pgvector extension reports version 0.8.5.
- The extension is enabled through a migration rather than an initialization script.
- The database remains available after a normal stop and restart.
- `docker compose down` stops predictably without deleting the named volume.
- No database credential or local database data is tracked by Git.

## Reconsider when

Reconsider this decision if the project requires a hosted database, PostgreSQL 18 approaches end of support, the pgvector image is no longer maintained, a major-version upgrade is planned, or measured retrieval requirements cannot be met by PostgreSQL and pgvector.

## References

- [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
- [PostgreSQL official container image](https://hub.docker.com/_/postgres)
- [pgvector container image](https://hub.docker.com/r/pgvector/pgvector)
- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)