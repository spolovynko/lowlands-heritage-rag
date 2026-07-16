# ADR 0005: Use uv_build

- Status: Accepted
- Date: 2026-07-16

## Context

The project uses a single pure-Python package under `src/`. Phase 1 requires the project to be installable so that clean-install and import verification exercise the packaged code rather than importing accidentally from the repository root.

The generated `pyproject.toml` already referenced `uv_build`, but its use and version range had not been reviewed. Dependency management with `uv` was approved separately in ADR 0003.

## Decision drivers

- Support the approved single-package `src` layout.
- Install the project itself during environment synchronization.
- Prefer minimal configuration for a pure-Python package.
- Validate common packaging and project-structure mistakes.
- Bound breaking changes while the backend remains in a `0.x` release series.
- Avoid flexibility that the project does not currently need.

## Considered options

1. Use `uv_build`.
2. Use Hatchling.
3. Use setuptools.

## Decision

Use `uv_build` as the Python build backend.

Declare the build requirement as:

`uv_build>=0.11.28,<0.12`

The project will use the backend’s standard single-package `src` layout without custom build hooks or inclusion rules.

Dependency management and build-backend responsibilities remain conceptually separate even though both selected tools are provided by the `uv` project.

## Consequences

### Positive

- The approved package layout requires little or no backend-specific configuration.
- The backend validates project metadata and expected package structure.
- Local synchronization can install the project as an editable package.
- The upper version bound prevents unreviewed breaking backend changes.

### Negative

- `uv_build` does not support compiled extension modules.
- The project depends on a comparatively focused backend rather than the more flexible Hatchling or setuptools ecosystems.
- Moving outside the backend’s supported layouts would require configuration or migration.

### Neutral

- Build dependencies are resolved separately from application dependencies.
- The installed `uv` command and the selected `uv_build` package do not need identical patch versions.

## Validation

- Dependency resolution can obtain a compatible `uv_build` version.
- A source distribution and wheel build successfully.
- The built wheel contains the `lowlands_lens` package.
- The installed distribution can be imported as `lowlands_lens`.
- Building does not include local data, secrets, caches, or test artifacts unintentionally.

## Reconsider when

Reconsider this decision if the project requires compiled extension modules, custom build scripts, multiple top-level packages, unsupported file-layout behavior, or recurring backend compatibility problems.

## References

- [uv build-backend documentation](https://docs.astral.sh/uv/configuration/build-backend/)
- [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [ADR 0001: Use a single-package src layout](0001-use-a-single-package-src-layout.md)
- [ADR 0003: Use uv for dependency management](0003-use-uv-for-dependency-management.md)
- [ADR 0004: Use the Lowlands Lens package identity](0004-use-the-lowlands-lens-package-identity.md)