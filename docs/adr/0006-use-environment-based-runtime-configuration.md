# ADR 0006: Use environment-based runtime configuration

- Status: Accepted
- Date: 2026-07-16

## Context

Later phases will introduce database connection settings and external service credentials. Phase 1 must establish configuration and secret boundaries before those values exist.

The project currently has no runtime settings and requires no credentials. Configuration code or dependencies added before a real consumer exists would be speculative.

## Decision drivers

- Prevent credentials from entering version control.
- Keep local development settings convenient but clearly local.
- Make supported settings discoverable without publishing secrets.
- Keep configuration behavior consistent across local processes, CI, and future containers.
- Avoid configuration dependencies before application settings exist.
- Ensure missing required values fail clearly.

## Considered options

1. Use environment variables without documented examples.
2. Store runtime configuration in committed files.
3. Use environment variables with ignored local files and safe committed documentation.
4. Introduce a dedicated local secret-management service.

## Decision

Use environment variables for deployment-specific runtime configuration and all secrets.

Application-owned environment variables will use the `LOWLANDS_LENS_` prefix. Variables required directly by external tools or container images may retain the names required by those systems.

Local values may be stored in `.env` or environment-specific `.env.*` files. These local files must be ignored by Git.

A committed `.env.example` may document settings only after real settings exist. It may contain variable names, comments, and non-sensitive example values. It must never contain working credentials, tokens, private URLs, or copied local values.

When a tool supports both process environment variables and a local `.env` file, explicit process environment variables take precedence.

Tool configuration that is safe to commit belongs in `pyproject.toml` or the relevant versioned tool