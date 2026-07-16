# ADR 0001: Use a single-package src layout

- Status: Accepted
- Date: 2026-07-16

## Context

Phase 1 requires the smallest Python foundation that can be installed, imported, and tested reproducibly. The repository may later contain ingestion, retrieval, API, and evaluation code, but those capabilities do not yet require independently packaged services.

The existing scaffold contains Python code below `src/`. This decision evaluates only that layout pattern. It does not approve the Python version, dependency manager, build backend, distribution name, import-package name, command-line entry point, or current package contents.

## Decision drivers

- Detect packaging and import errors early.
- Keep importable code separate from tests, documentation, migrations, and local data.
- Support later internal modules without creating premature service boundaries.
- Keep the Phase 1 foundation small.

## Considered options

1. Place Python modules directly in the repository root.
2. Use one importable Python package below `src/`.
3. Create multiple packages or service directories immediately.

## Decision

Use a single-package `src` layout.

Importable Python code will live below `src/<import-package>/`. Tests and non-Python resources will remain outside `src/`. Internal subpackages will be introduced only when a later phase requires them.

The import-package name will be decided separately.

## Consequences

### Positive

- Tests exercise an installed package rather than importing accidentally from the repository root.
- Python code has a clear ownership boundary.
- Later capabilities can be organized as internal modules without reorganizing the repository.

### Negative

- Local development requires the package to be installed in the active environment.
- The layout adds one directory level.

### Neutral

- The repository name, distribution name, and Python import-package name may differ.
- Infrastructure and data directories remain subject to later Phase 1 decisions.

## Validation

- A clean environment can install the project.
- The selected package can be imported after installation.
- Unit tests import the installed package successfully.

## Reconsider when

Reconsider the single-package boundary if components require independent releases, incompatible dependency lifecycles, or separate deployment ownership.

## References

- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)