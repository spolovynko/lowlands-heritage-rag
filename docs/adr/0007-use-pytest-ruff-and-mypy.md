# ADR 0007: Use pytest, Ruff, and mypy

- Status: Accepted
- Date: 2026-07-16

## Context

Phase 1 requires automated unit testing, linting, formatting checks, and static type checking before application or data-pipeline logic is introduced.

The project needs a small quality toolchain whose commands can run identically during local development and continuous integration. Overlapping tools would add configuration and maintenance without improving the current foundation.

## Decision drivers

- Detect defects before application logic grows.
- Use the same checks locally and in continuous integration.
- Minimize overlapping tools and configuration.
- Support Python 3.14.
- Keep unit tests independent of external services.
- Establish strict typing while the codebase is still small.
- Avoid speculative coverage targets and workflow tools.

## Considered options

1. Use standard-library `unittest`, separate Flake8, isort, and Black tools, and mypy.
2. Use pytest, Ruff for linting and formatting, and mypy.
3. Use pytest, Ruff, and a different static type checker such as Pyright.
4. Introduce an additional task runner or pre-commit framework.

## Decision

Use pytest for unit testing.

Use Ruff for linting, import sorting, and formatting.

Use mypy in strict mode for static type checking.

Store pytest, Ruff, and mypy configuration in `pyproject.toml`.

Unit tests will live under `tests/`, use filenames matching `test_*.py`, and use test functions named `test_*`. Unit tests must not require network access, credentials, containers, PostgreSQL, or other running services.

Static type checking will cover both `src/` and `tests/`.

Local and continuous-integration verification will use these commands:

- `pytest`
- `ruff check .`
- `ruff format --check .`
- `mypy src tests`

Continuous integration will run checks without automatic fixes. Developers may apply explicit Ruff fixes locally and review the resulting changes.

Phase 1 will not introduce a coverage threshold, pre-commit framework, or separate task runner.

## Consequences

### Positive

- One tool handles linting, import sorting, and formatting.
- Tests use concise assertions and standard discovery conventions.
- Strict typing starts before untyped application code accumulates.
- Local and CI checks share the same configuration and commands.
- Unit tests remain fast and independent.

### Negative

- Contributors must install three development dependencies.
- Strict mypy may require deliberate annotations as integrations are added.
- Ruff formatting may differ slightly from other formatter ecosystems.

### Neutral

- Exact dependency versions are selected by the committed lockfile.
- Coverage measurement may be introduced later when meaningful logic exists.
- Integration and infrastructure tests will require separate markers or workflows when those tests exist.

## Validation

- pytest discovers and passes the minimal unit test.
- Ruff linting passes without automatic fixes.
- Ruff formatting checks pass without modifying files.
- Strict mypy passes for `src/` and `tests/`.
- Unit tests pass without credentials, network access, containers, or PostgreSQL.
- The same commands run successfully in continuous integration.

## Reconsider when

Reconsider this decision if a selected tool does not support the approved Python version, creates recurring compatibility problems, or another tool provides a measured simplification without weakening the quality gates.

## References

- [pytest documentation](https://docs.pytest.org/en/stable/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [mypy documentation](https://mypy.readthedocs.io/en/stable/)
- [ADR 0002: Use Python 3.14](0002-use-python-3-14.md)
- [ADR 0003: Use uv for dependency management](0003-use-uv-for-dependency-management.md)