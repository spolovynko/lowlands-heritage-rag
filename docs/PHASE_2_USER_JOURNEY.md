# Phase 2 user journey

## Purpose

Phase 2 demonstrates the Lowlands Lens public API and interface behavior before
real Europeana ingestion, retrieval, or answer generation is implemented.

All cultural records, institutions, descriptions, dates, and source links in
this phase are deterministic fictional fixtures. The prototype makes no claim
about Europeana content, coverage, relevance, or data quality.

## Start the application

From the repository root:

```powershell
uv sync --locked
uv run --locked uvicorn lowlands_lens.api.app:app --host 127.0.0.1 --port 8000
```

Open:

- Interface: <http://127.0.0.1:8000/>
- OpenAPI documentation: <http://127.0.0.1:8000/docs>
- Liveness: <http://127.0.0.1:8000/api/v1/health>

The Phase 2 application does not use the PostgreSQL service. No `.env` file,
credential, Europeana access, external API, embedding model, or answer model is
required.

Stop the application with `Ctrl+C` in its terminal.

## Progressive journey

The interface is a single conversational thread. Searches, evidence cards,
answers, abstentions, and errors all appear as messages, so the complete
journey stays visible and inspectable from top to bottom.

### 1. Search

Choose English, French, or Dutch in the chat composer, keep the composer in
**Search** mode, and submit a query. Useful deterministic examples are:

| Query | Expected state |
| --- | --- |
| `poster` | One synthetic poster result |
| `Bruxelles` | One synthetic photograph result |
| `haven` | One synthetic audio result |
| `no matching object` | Valid empty search |
| `simulate-search-error` | Structured search-unavailable error |

Each returned evidence card displays:

- a synthetic-data label;
- multilingual title and description;
- media and object type;
- fictional date;
- provider and data-provider attribution (in the “Provenance & rights”
  disclosure);
- record, provider, or digital-object links;
- separate metadata and digital-object rights;
- the visible mock-retrieval limitation.

An empty search is a successful response. It is intentionally different from
the operational error demonstration.

### 2. Select evidence

Select one or more evidence cards with their toggle. Selected records appear
as removable chips in the evidence tray above the composer, and the composer
gains an **Ask** mode. Only selected evidence identifiers are sent to the
answer endpoint. Earlier search results remain visible in the thread
throughout the answer operation.

### 3. Request an answer

Switch the composer to **Ask** and submit a question about the selected
records. The Phase 2 answer generator is deterministic and does not use an AI
model. Useful examples are:

| Question | Expected state |
| --- | --- |
| `What do the selected synthetic records demonstrate?` | Answer with citations |
| `Who was objectively the most influential Belgian artist?` | Unsupported-question abstention |
| `simulate-generation-unavailable` | Generation unavailable while evidence remains visible |

The answered response cites only selected evidence identifiers. Citations and
labels are constructed by the application. The mock answer explicitly states
that synthetic records establish no historical fact.

## API summary

All public endpoints use the major-version prefix `/api/v1`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Process liveness and contract version |
| `POST` | `/api/v1/search` | Search for object-level evidence |
| `POST` | `/api/v1/answer` | Answer from selected evidence identifiers |

### Search request

```json
{
  "query": "poster",
  "language": "en",
  "limit": 10
}
```

Search returns either `outcome: "results"` or `outcome: "empty"`. A dependency
failure instead returns a structured non-success response:

```json
{
  "error": {
    "code": "search_unavailable",
    "message": "Search is temporarily unavailable in the Phase 2 prototype.",
    "field_errors": [],
    "request_id": null
  }
}
```

### Answer request

```json
{
  "question": "What does this synthetic record demonstrate?",
  "language": "en",
  "evidence_ids": ["synthetic-poster-001"]
}
```

The discriminated answer response has one of three outcomes:

- `answered`: non-empty answer text and citations;
- `abstained`: no answer text, a reason, and visible limitations;
- `generation_unavailable`: no answer text, an availability reason, and
  visible limitations.

Unknown evidence identifiers return a structured `not_found` error rather than
being silently ignored.

## Internal replacement boundary

The application factory receives three small ports:

- `Retriever` searches for evidence;
- `EvidenceRepository` resolves selected identifiers;
- `AnswerGenerator` produces an answer outcome from supplied evidence.

Phase 7 can replace the in-memory retriever with the evaluated lexical baseline.
Phase 10 can replace deterministic generation with an evaluated model-backed
adapter. Neither replacement should require a public API redesign.

## Verification

Run from the repository root:

```powershell
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv build
```

The test suite covers contracts, fixture retrieval, answer outcomes, versioned
endpoints, structured errors, dependency replacement, static asset serving, and
required interface states.

## Phase boundaries

Phase 2 deliberately excludes:

- Europeana API access and credentials;
- production database integration;
- real ingestion or normalization;
- lexical, vector, or hybrid retrieval;
- embeddings and reranking;
- prompts, LLMs, agents, and Pydantic AI;
- production citation validation;
- production authentication, deployment, or monitoring infrastructure.
