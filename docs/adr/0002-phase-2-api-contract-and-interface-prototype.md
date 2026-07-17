# ADR 0002: Phase 2 API contract and interface prototype

- Status: Accepted
- Date: 2026-07-17
- Scope: Phase 2 — API contract and interface prototype
- Supersedes: Individual Phase 2 ADRs 0002 and 0003

## Context

Phase 2 makes the intended Lowlands Lens product behavior visible before real
Europeana data, retrieval, or answer generation exists. It needs a complete
local search-then-answer journey with stable public contracts, explicit
evidence and rights, deterministic synthetic records, and replaceable internal
components.

The implementation must preserve the Phase 1 Python, uv, quality, packaging,
configuration, and CI conventions. It must not require credentials, external
APIs, a production database, retrieval models, embeddings, prompts, or an
answer model.

This record aggregates every consequential Phase 2 decision. Phase 1 remains
documented separately in ADR 0001.

## Decision summary

| ID | Topic | Decision |
| --- | --- | --- |
| P2-D01 | User journey | Progressive search first, then optional answer generation |
| P2-D02 | API boundary | FastAPI and Pydantic Validation |
| P2-D03 | AI framework | Defer Pydantic AI and all model integration to Phase 10 |
| P2-D04 | Interface | Separate static HTML, CSS, and vanilla JavaScript served by FastAPI |
| P2-D05 | Versioning | Major-version path prefix `/api/v1` and contract version `1.0.0` |
| P2-D06 | Contracts | Strict request, response, evidence, citation, rights, outcome, and error models |
| P2-D07 | Internal design | Framework-independent domain records and small typed ports |
| P2-D08 | Mock adapters | Deterministic in-memory retrieval and answer generation |
| P2-D09 | Synthetic data | Small, fictional, labelled, reproducible runtime fixtures |
| P2-D10 | Failure semantics | Empty, operational error, abstention, and unavailability remain distinct |
| P2-D11 | Testing | Contract, component, endpoint, interface-state, packaging, and browser checks |

## Decisions

### P2-D01 — Progressive search-then-answer journey

The interface performs search as an independent first operation. Returned
evidence remains visible and selectable while the user requests an answer in a
second operation.

Answer abstention or unavailability never removes successful search results.
This preserves a useful evidence-discovery journey when a future answer model
cannot or should not answer.

### P2-D02 and P2-D03 — API framework and deferred AI integration

Use FastAPI for the local HTTP API and Pydantic Validation for public transport
models, validation, JSON Schema, and OpenAPI generation.

Pydantic Validation and Pydantic AI solve different problems. Do not add
Pydantic AI in Phase 2. In Phase 10, compare it with a direct provider SDK and
with using no agent framework. Any selected model-backed adapter must implement
the existing answer-generation port without changing the public API contract.

Do not pass FastAPI request objects, response objects, or Pydantic AI types into
application ports.

### P2-D04 — One-process static interface

Serve the local interface and versioned API from one FastAPI process. Use
separate package-owned files:

- `index.html` for semantic structure;
- `styles.css` for presentation and responsive behavior;
- `app.js` for Fetch API calls and interface state.

Use no template engine, Streamlit, Gradio, JavaScript framework, Node.js,
frontend package manager, bundler, external font, or content-delivery network.
The browser consumes only the public HTTP contract.

### P2-D05 and P2-D06 — Versioned strict contracts

Expose the Phase 2 API under `/api/v1` and publish contract version `1.0.0` in
OpenAPI and the liveness response.

Use opaque string identifiers. Support `en`, `fr`, and `nl` for questions and
answers while allowing broader language tags on source metadata.

Public contracts explicitly represent:

- search and answer requests;
- results and valid empty searches;
- object-level evidence;
- multilingual titles and descriptions;
- provider and data-provider roles;
- record, provider, and digital-object links;
- separate metadata and digital-object rights;
- application-controlled citations;
- answered, abstained, and generation-unavailable outcomes;
- structured validation and operational errors;
- visible limitations and liveness.

Contracts reject unknown fields, trim string whitespace, validate bounds, and
enforce cross-field invariants. Missing rights remain unknown and never imply
reuse permission.

### P2-D07 and P2-D08 — Ports and replaceable adapters

Use immutable framework-independent domain records. Define small structural
interfaces for:

- searching for evidence;
- resolving evidence identifiers;
- generating an answer from an explicit evidence package.

The FastAPI application factory receives these dependencies through an
`ApplicationServices` container. API mappers own translation between internal
records and Pydantic transport models.

The default local application uses an in-memory retrieval adapter and a
deterministic answer generator. Later phases replace these adapters rather than
changing route semantics or public schemas.

### P2-D09 — Synthetic fixtures

Keep three small, deterministic fictional records in package-owned Python data.
They exercise English, French, and Dutch text; image and sound media; provider
roles; source links; known and unknown digital-object rights; results and empty
searches; answers; abstention; and unavailable generation.

Every record and institution name is labelled synthetic. Reserved example
links are used. Fixtures contain no downloaded media, Europeana response,
credential, local production data, or claim about Europeana coverage.

### P2-D10 — Explicit state semantics

Treat a valid empty search as HTTP 200 with `outcome: empty`. Treat retrieval
unavailability as an operational error with HTTP 503 and a structured error
body.

Treat abstention as a successful answer operation whose evidence is
insufficient or whose requested conclusion is unsupported. Treat generation
unavailability as a separate successful search-preserving outcome. Neither is
represented as an empty string or generic server error.

Use documented deterministic trigger phrases only to demonstrate Phase 2
states. They are mock implementation details and are not part of the long-term
retrieval or generation design.

### P2-D11 — Verification and CI

Use pytest for contract, adapter, endpoint, dependency-replacement, and static
interface tests. Use FastAPI's in-process test client with `httpx2` as a bounded
development dependency.

Retain Ruff linting and formatting plus strict mypy. CI runs the locked
installation and the same quality suite. Build the wheel to verify that static
assets are packaged, and complete a local HTTP and browser journey before the
Phase 2 exit gate.

## Consequences

### Positive

- The complete product journey is visible before production data work.
- Public contracts and outcome semantics can remain stable across later phases.
- Retrieval and generation adapters are independently replaceable.
- Search remains useful when answering abstains or is unavailable.
- All required evidence, attribution, rights, and limitations are inspectable.
- One local process and no frontend toolchain keep operation simple.
- The prototype is deterministic and requires no secret or external service.

### Negative

- Domain records and public transport models require explicit mapping.
- Handwritten browser state management is appropriate only while the interface
  remains small.
- The deterministic search and answer behavior demonstrates contracts, not
  retrieval relevance, grounding quality, or historical correctness.
- Trigger phrases used to demonstrate failures are intentionally artificial.

### Neutral

- Pydantic at the API boundary does not require Pydantic models throughout the
  application.
- A synchronous Phase 2 port does not prevent asynchronous adapters later when
  measured requirements justify them.
- Static interface assets may be replaced later without changing `/api/v1`.
- Existing PostgreSQL and migration foundations remain present but unused by
  the Phase 2 journey.

## Validation

The decision is validated when:

- `/`, `/docs`, and `/api/v1/health` start locally;
- search returns results and a valid empty response;
- operational search errors use the error contract;
- answered, abstained, and generation-unavailable responses validate;
- providers, links, rights, evidence, citations, and limitations are visible;
- search evidence remains visible during answer operations;
- dependency replacement is proven by an application-factory test;
- static files are separate, package-owned, and present in the built wheel;
- pytest, Ruff, formatting, and strict mypy pass;
- the interface is checked in a local browser;
- no credential, Europeana call, production database, embedding, prompt, or
  answer model is required.

## Reconsider when

Reconsider the relevant decision when the public contract cannot express a
measured requirement; adapter replacement forces HTTP redesign; asynchronous
dependencies require a revised port; interface complexity justifies a
component framework; streaming becomes necessary; a new major public contract
is required; or Phase 10 evidence shows that Pydantic AI materially improves a
model-backed implementation.

## References

- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)
- [Phase 2 user journey](../PHASE_2_USER_JOURNEY.md)
- [Phase 1 repository foundation](0001-phase-1-repository-foundation.md)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [HTTPX2](https://httpx2.pydantic.dev/)
