# ADR 0003: Use uv for dependency management

- Status: Accepted
- Date: 2026-07-16

## Context

Phase 1 requires deterministic dependency resolution and a reproducible clean-install workflow. The project needs to separate broad dependency requirements from the exact versions installed locally and in continuous integration.

`uv 0.11.6` is already installed locally. The existing `pyproject.toml` mentions `uv_build`, but the build backend is a separate decision and is not approved by this ADR.

## Decision drivers

- Produce deterministic dependency installations.
- Use one documented local and CI workflow.
- Keep dependency declarations in standard `pyproject.toml` fields.
- Support development-only dependency groups.
- Avoid introducing multiple overlapping dependency tools.
- Make dependency upgrades explicit and reviewable.

## Considered options

1. Use pip with requirements files or its experimental lock command.
2. Use Poetry or PDM as an integrated project manager.
3. Use `uv` with its project workflow and `uv.lock`.

## Decision

Use `uv 0.11.x` for project dependency management and locking.

Runtime dependencies will be declared in `[project].dependencies`. Development-only tools will be declared in standard dependency groups.

The generated `uv.lock` file will be committed to version control and must not be edited manually. The local `.venv/` directory will remain ignored.

Reproducible installation and CI will use locked synchronization. A stale or missing lockfile must cause verification to fail rather than being silently updated.

Dependency upgrades will be explicit operations reviewed through changes to `pyproject.toml` and `uv.lock`.

This decision does not select or approve a Python build backend.

## Consequences

### Positive

- Local development and CI can install the same resolved dependency versions.
- One tool handles resolution, locking, synchronization, and command execution.
- The lockfile supports cross-platform dependency resolution.
- Dependency upgrades produce inspectable version-control changes.

### Negative

- `uv.lock` is specific to `uv`.
- Contributors must use a compatible `uv 0.11.x` release.
- Future `uv` minor versions may require a reviewed lockfile migration.

### Neutral

- `pyproject.toml` remains the source of direct dependency intent.
- The lockfile is generated project state that is committed but not manually maintained.
- The build backend remains a separate architecture choice.

## Validation

- `uv lock --check` confirms that `uv.lock` agrees with `pyproject.toml`.
- `uv sync --locked` succeeds from a clean environment.
- The installed package can be imported after synchronization.
- CI uses a compatible `uv 0.11.x` version and refuses stale lockfiles.
- No `.venv/` content is committed.

## Reconsider when

Reconsider this decision if `uv` cannot resolve an essential dependency, its lockfile becomes unsuitable for supported platforms, a standardized lock workflow becomes stable and materially improves interoperability, or maintaining `uv` creates measurable operational problems.

## References

- [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [uv project layout and lockfile](https://docs.astral.sh/uv/concepts/projects/layout/)
- [pip lock documentation](https://pip.pypa.io/en/stable/cli/pip_lock/)
- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)