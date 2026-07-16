# ADR 0004: Use the Lowlands Lens package identity

- Status: Accepted
- Date: 2026-07-16

## Context

The approved product working name is Lowlands Lens. The repository is named `lowlands-heritage-rag`.

An earlier generated scaffold used `lowlands-heritage-rag` as the distribution name, `lowlands_heritage_rag` as the Python import package, and created a command-line entry point that prints a greeting. Those choices were generated before review.

Phase 1 requires only one minimal package that can be installed, imported, and tested. It does not require an application command or other product features.

## Decision drivers

- Align the Python package with the approved product identity.
- Keep imports concise and understandable.
- Avoid tying the package identity permanently to one implementation technique.
- Establish only the smallest Phase 1 package.
- Avoid adding an unneeded command-line interface.

## Considered options

1. Keep `lowlands-heritage-rag` as the distribution and `lowlands_heritage_rag` as the import package.
2. Use `lowlands-lens` as the distribution and `lowlands_lens` as the import package.
3. Create multiple top-level Python packages.

## Decision

Use `lowlands-lens` as the distribution name.

Use `lowlands_lens` as the single top-level Python import package under `src/`.

The repository will remain named `lowlands-heritage-rag`.

The Phase 1 package will contain only the minimal initialization needed to verify installation and import. It will not define a command-line entry point or produce output when imported.

Internal subpackages and application entry points will be added only when a later approved phase requires them.

## Consequences

### Positive

- The import package matches the Lowlands Lens product identity.
- The package name remains appropriate as the architecture evolves.
- Imports are shorter than the generated repository-derived name.
- Phase 1 contains no speculative application interface.

### Negative

- The generated package directory must be renamed.
- Existing generated project metadata must be corrected.

### Neutral

- The repository, distribution, and import package use related but different names.
- Future entry points require a separate approved implementation step.

## Validation

- The distribution metadata identifies the project as `lowlands-lens`.
- `import lowlands_lens` succeeds after a clean installation.
- `import lowlands_heritage_rag` is not required.
- Project metadata contains no Phase 1 command-line entry point.
- Importing the package produces no output or side effects.

## Reconsider when

Reconsider the package boundary if independently released components become necessary or the approved product name changes.

## References

- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)
- [ADR 0001: Use a single-package src layout](0001-use-a-single-package-src-layout.md)