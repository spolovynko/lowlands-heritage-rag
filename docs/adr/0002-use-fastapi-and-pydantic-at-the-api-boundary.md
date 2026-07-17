# ADR 0002: Use FastAPI and Pydantic at the API boundary

- Status: Accepted
- Date: 2026-07-17
- Scope: Phase 2 - API contract and interface prototype

## Context

Phase 2 requires a versioned local API that exposes stable search and answer
contracts before real ingestion, retrieval, or answer generation exists.

The API must validate requests and responses, describe evidence and citations,
represent expected failure and limitation states, generate inspectable contract
documentation, and support endpoint tests. Mock retrieval and answer-generation
implementations must remain replaceable without changing the public contract.

The solution design listed FastAPI as provisional. FastAPI, Pydantic, and other
interface technologies were not approved by Phase 1.

Pydantic Validation and Pydantic AI serve different purposes. Pydantic
Validation can define and validate HTTP request and response models. Pydantic AI
is a generative-AI agent framework that would introduce model orchestration
concerns outside the Phase 2 boundary.

## Decision drivers

- Define explicit, typed request and response contracts.
- Generate OpenAPI and JSON Schema from reviewed contract definitions.
- Validate API inputs and outputs consistently.
- Support contract and endpoint testing without starting a network service.
- Preserve the approved strict typing and pytest conventions.
- Keep retrieval and answer generation independent from the HTTP framework.
- Avoid model, agent, credential, database, and production integration work.
- Keep the Phase 2 application skeleton small.

## Considered options

1. Use FastAPI with Pydantic models at the HTTP boundary.
2. Use Starlette and select or implement validation and schema generation
   separately.
3. Use Flask and add manual schemas or API-contract extensions.

## Decision

Use FastAPI as the Phase 2 HTTP API framework.

Use Pydantic models to define and validate public API requests, responses, and
structured error bodies. Generate the API's OpenAPI and JSON Schema
representations from those reviewed models.

Keep FastAPI routing and Pydantic transport models at the API boundary.
Retrieval and answer-generation components will communicate through small,
framework-independent typed Python interfaces. Those interfaces must not accept
or return FastAPI request objects, FastAPI response objects, or Pydantic
AI-specific types.

Provide deterministic Phase 2 mock implementations behind the retrieval and
answer-generation interfaces.

Do not adopt Pydantic AI during Phase 2. Reconsider Pydantic AI in Phase 10 as
one possible implementation of the real answer-generation adapter. Compare it
with a direct model-provider SDK and with the option of using no agent framework.

This decision does not approve:

- exact FastAPI, Pydantic, ASGI server, or testing-library versions;
- a FastAPI optional dependency bundle;
- the local interface technology;
- Pydantic Settings;
- Pydantic AI;
- an answer model or model provider;
- model-controlled tools or an agent loop;
- Europeana access or credentials;
- production database integration;
- authentication, deployment, or monitoring infrastructure.

Those choices require their appropriate Phase 2 step or later implementation
phase.

## Consequences

### Positive

- API contracts can be validated and exposed through OpenAPI and JSON Schema.
- Request, response, and structured error behavior can be tested directly.
- The contract definitions use the same modern Python typing approach as the
  existing strict mypy convention.
- Later retrieval and generation adapters can replace mocks without changing
  endpoint semantics.
- Pydantic AI remains available for evidence-based evaluation in Phase 10.

### Negative

- FastAPI introduces Starlette and Pydantic as dependencies.
- Pydantic transport models can spread into application logic unless the
  boundary is enforced deliberately.
- Framework and schema-library upgrades may affect generated OpenAPI output.
- Exact compatibility with Python 3.14 must be verified through locked
  dependency resolution and the full quality suite.

### Neutral

- Selecting FastAPI does not select the local interface framework.
- Selecting Pydantic for transport validation does not require Pydantic models
  for every internal domain type.
- Selecting an asynchronous-capable framework does not require every function
  or mock implementation to be asynchronous.
- A separate ASGI server is still required to start the local API and will be
  selected with the application dependency and startup convention.

## Validation

- Resolve approved bounded dependency versions under Python 3.14 using uv.
- Confirm the locked environment installs cleanly.
- Confirm the FastAPI application imports without side effects.
- Generate and inspect the OpenAPI document.
- Test valid and invalid requests through an in-process test client.
- Test declared response models and structured error responses.
- Confirm mock retrieval and answer-generation implementations can be replaced
  through their interfaces without changing public schemas.
- Run pytest, Ruff linting, Ruff formatting checks, and strict mypy.
- Confirm the Phase 2 journey requires no credentials, external API, model, or
  production database.

## Reconsider when

Reconsider this decision if FastAPI or Pydantic cannot support the approved
Python version, generated schemas cannot express the reviewed contract,
framework coupling prevents adapter replacement, contract testing becomes
unreliable, or another framework provides a measured simplification without
weakening validation, documentation, typing, or testability.

Evaluate Pydantic AI separately in Phase 10 when a real answer-generation
adapter, model access, structured model output, prompt design, citation
validation, and grounding evaluation enter scope.

## References

- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)
- [Phase 1 repository foundation](0001-phase-1-repository-foundation.md)
- [FastAPI features](https://fastapi.tiangolo.com/features/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic AI](https://pydantic.dev/docs/ai/overview/)