# ADR 0010: Use GitHub Actions for basic continuous integration

- Status: Accepted
- Date: 2026-07-16

## Context

Phase 1 requires continuous integration that reproduces the project's agreed
quality checks on a clean hosted runner. The repository is hosted on GitHub and
uses Python 3.14, uv, and a committed lockfile.

The initial workflow must remain small. It should validate the repository
foundation without introducing application deployment, credentials, database
services, or Phase 2 behavior.

## Decision drivers

- Run the agreed checks on every pushed change and pull request
- Install dependencies exactly from the committed lockfile
- Use the project's approved Python and uv versions
- Require no repository credentials beyond read-only source access
- Keep the workflow understandable and inexpensive
- Match commands developers can run locally

## Considered options

1. GitHub Actions with one Ubuntu quality job
2. Another hosted CI provider
3. Local checks only
4. A multi-platform or database-backed CI matrix in Phase 1

## Decision

Use GitHub Actions for basic continuous integration.

Run one job on `ubuntu-latest` for pushes and pull requests. Grant only
read-only repository-content permission.

Use the Python version declared in `.python-version` and uv version `0.11.6`.
Install the project and development dependencies with `uv sync --locked`.

Run these checks:

1. Verify the package can be imported.
2. Run pytest.
3. Run Ruff linting.
4. Run the Ruff formatting check.
5. Run strict mypy using the project configuration.

Do not add PostgreSQL, pgvector, migrations, deployment, publishing, or secrets
to the basic CI workflow. Infrastructure reproducibility is validated through
the separate Phase 1 local exit gate.

## Consequences

### Positive

- Pull requests and pushed commits receive repeatable quality feedback.
- The workflow exercises a clean locked installation.
- CI commands remain identical to local commands.
- The workflow needs no project secrets.
- One job keeps runtime and maintenance cost low.

### Negative

- The initial workflow covers only the Ubuntu runner environment.
- Database migration behavior is not exercised by basic CI.
- GitHub Actions availability becomes part of the contribution workflow.

### Neutral

- Windows remains covered by local development and exit-gate verification.
- Additional operating systems or database services require measured need and a
  later decision.

## Validation

- Validate the workflow file structure by review.
- Run every workflow command locally from the locked environment.
- Push the workflow and confirm the GitHub Actions job succeeds.
- Confirm the workflow requests no write permission and uses no secrets.

## Reconsider when

- Platform-specific failures justify a test matrix.
- Migration regressions justify a PostgreSQL CI service.
- CI duration or reliability no longer meets project needs.
- The repository moves away from GitHub.

## References

- [Implementation phases](../IMPLEMENTATION_PHASES.md)
- [Using uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [GitHub Actions documentation](https://docs.github.com/actions)
