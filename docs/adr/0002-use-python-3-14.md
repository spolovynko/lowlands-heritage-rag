# ADR 0002: Use Python 3.14

- Status: Accepted
- Date: 2026-07-16

## Context

Phase 1 requires a consistent Python version for local development, dependency locking, testing, continuous integration, and future containers.

Python 3.14 and Python 3.12 are installed locally. Python 3.14 is the current default. Python 3.12 receives security fixes only, while Python 3.14 remains in the regular bug-fix phase and is supported until October 2030.

The existing `.python-version` and `pyproject.toml` were created before this decision and do not yet represent an approved version policy.

## Decision drivers

- Use a stable Python release with active bug-fix support.
- Avoid installing another Python version without a demonstrated need.
- Keep local development, CI, and future containers consistent.
- Prevent untested adoption of a future Python minor version.
- Allow compatible Python 3.14 patch updates.

## Considered options

1. Use Python 3.12.
2. Install and use Python 3.13.
3. Use the installed Python 3.14 runtime.
4. Use a Python 3.15 prerelease.

## Decision

Use Python 3.14 as the project runtime.

Project metadata will declare:

`requires-python = ">=3.14,<3.15"`

Local development, CI, and future application containers will use Python 3.14. An exact patch version may be selected by the approved environment and dependency-management convention, but the project compatibility boundary remains the Python 3.14 minor series.

## Consequences

### Positive

- The selected runtime is already installed locally.
- Python 3.14 receives regular bug fixes and has a long support window.
- Local development and future automation can share one minor version.
- Python 3.15 will not be adopted accidentally before validation.

### Negative

- Some third-party packages may adopt Python 3.14 later than older versions.
- Contributors without Python 3.14 must install it.

### Neutral

- Patch releases within Python 3.14 may change over the project lifetime.
- Dependency compatibility must still be validated through clean installation.

## Validation

- The selected interpreter reports Python 3.14.
- Dependency resolution succeeds under Python 3.14.
- The package imports under Python 3.14.
- Tests and quality checks run under Python 3.14.
- CI and future containers use the same Python minor version.

## Reconsider when

Reconsider this decision if an essential dependency does not support Python 3.14, the target runtime cannot provide Python 3.14, or a later Python version provides a measured project benefit and passes the full test suite.

## References

- [Python version status](https://devguide.python.org/versions/)
- [Python 3.14.6 release](https://www.python.org/downloads/release/python-3146/)
- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)