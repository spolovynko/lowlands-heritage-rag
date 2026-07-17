# ADR 0003: Serve a static interface from FastAPI

- Status: Accepted
- Date: 2026-07-17
- Scope: Phase 2 - API contract and interface prototype

## Context

Phase 2 requires the smallest complete local interface for the approved
progressive search-then-answer journey.

The interface must submit requests through the public API and display synthetic
search results, evidence, citations, providers, source links, rights,
limitations, loading states, empty results, structured errors, abstention, and
generation-unavailable behavior.

The interface must remain small and locally reproducible. It must not introduce
a second application stack that obscures the API contract or adds unrelated
build and deployment machinery.

The API framework decision does not determine the local interface technology.
Streamlit and a separate JavaScript frontend were provisional possibilities
that required review.

## Decision drivers

- Exercise the versioned API through real HTTP requests.
- Keep search useful when answer generation abstains or is unavailable.
- Display every required state explicitly.
- Run the interface and API through one local application process.
- Avoid a second service and cross-origin configuration.
- Avoid Node.js, a frontend package manager, and a frontend build process.
- Keep page structure, presentation, and behavior understandable.
- Preserve the option to replace the interface later if measured needs grow.
- Require no credentials, external API, model, or production database.

## Considered options

1. Serve static HTML, CSS, and vanilla JavaScript from FastAPI.
2. Run Streamlit as a separate Python interface.
3. Build and run a separate JavaScript-framework frontend.

## Decision

Serve the Phase 2 local interface from the same FastAPI application as the
versioned API.

Use browser-native HTML, CSS, and JavaScript without a frontend framework.

Keep the interface concerns in separate files:

- HTML defines semantic page structure and visible content.
- CSS defines presentation and responsive layout.
- JavaScript calls the public API, updates the document, and manages interface
  states.

Do not place the complete interface, styles, and behavior into one inline HTML
file.

Use the browser Fetch API to call the versioned search and answer endpoints over
the same local origin.

The interface must consume only the public HTTP contract. It must not import or
call mock retrieval, mock answer generation, or internal application services
directly.

The FastAPI application will serve the interface entry page and its static
assets. The exact package-owned asset directory and filenames will be selected
during the local application-skeleton step and verified in the built package.

Do not introduce during Phase 2:

- Streamlit;
- Gradio;
- Jinja2 or another template engine;
- HTMX or another browser interaction library;
- React, Vue, Svelte, or another JavaScript framework;
- Node.js or a frontend package manager;
- a frontend compilation or bundling step;
- a separate interface service;
- assets loaded from an external content-delivery network.

This decision does not approve the detailed visual design, API field names,
endpoint paths, interface copy, or synthetic fixture contents. Those remain
subject to their Phase 2 design steps.

## Consequences

### Positive

- One local process serves both the API and interface.
- The browser exercises the same public contract that later clients can use.
- Same-origin requests require no cross-origin configuration.
- HTML, CSS, and JavaScript responsibilities remain visible and maintainable.
- No additional Python UI framework or JavaScript toolchain is required.
- Search results can remain visible while answer state changes independently.
- Static assets can be inspected directly by learners and reviewers.

### Negative

- Interface state and document updates require handwritten JavaScript.
- The project will not gain a component framework or its testing ecosystem.
- Comprehensive browser automation would require a separate dependency and
  decision.
- Shared interface components may become repetitive if the interface grows
  beyond the small Phase 2 prototype.

### Neutral

- FastAPI and Starlette provide the serving boundary, but do not control the
  interface's visual design.
- API and interface tests can run independently.
- Browser-level tests remain possible but are not automatically required by
  this decision.
- A later interface replacement would continue to use the versioned API
  contract.

## Validation

- Confirm the FastAPI application serves the interface entry page.
- Confirm HTML, CSS, and JavaScript are separate tracked files.
- Confirm static assets are included in a built wheel.
- Confirm static assets are returned with appropriate content types.
- Confirm JavaScript calls the versioned API rather than internal Python code.
- Confirm search and answer loading states are distinct.
- Confirm successful, empty, error, abstention, and
  generation-unavailable states are visible.
- Confirm search results remain visible during answer operations.
- Confirm synthetic records are clearly labelled.
- Confirm the interface uses no external assets or runtime network dependency.
- Confirm no Node.js, frontend build, or separate interface service is needed.
- Run the approved tests, linting, formatting checks, and strict type checking.
- Complete a manual local browser journey before the Phase 2 exit gate.

## Reconsider when

Reconsider this decision if the interface requires complex reusable components,
client-side routing, streaming interactions that become difficult to maintain,
stronger automated browser coverage, accessibility behavior that cannot be
implemented reliably, or a measured user-experience requirement justifies a
separate interface framework and build process.

## References

- [Solution design](../SOLUTION_DESIGN.md)
- [Implementation phases](../IMPLEMENTATION_PHASES.md)
- [API-framework decision](0002-use-fastapi-and-pydantic-at-the-api-boundary.md)
- [FastAPI frontend documentation](https://fastapi.tiangolo.com/tutorial/frontend/)
- [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/)
- [Streamlit application testing](https://docs.streamlit.io/develop/api-reference/app-testing)
