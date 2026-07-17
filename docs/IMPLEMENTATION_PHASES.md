# Lowlands Lens — Implementation Phases

## 1. Purpose

This roadmap divides implementation into production-style learning phases. Each phase explains:

- **Why** the phase exists
- **What** will be delivered
- **How** the work will be approached
- **What to learn** before or during implementation
- **How to verify** the result
- **Exit gate** required before proceeding

Phases are capability boundaries, not calendar estimates. Moving quickly means shortening feedback loops, not skipping baselines, tests, or evaluation.

## 2. Working agreement

Before each phase:

1. Review the proposed scope and affected files.
2. Confirm technology decisions and alternatives.
3. Approve the phase explicitly.

During each phase:

1. Implement one small, inspectable increment at a time.
2. Explain the logic and trade-offs.
3. Run relevant tests or experiments.
4. Review results before continuing.

No commit, push, external write, credential setup, container creation, or destructive action occurs without explicit approval.

## 3. Phase overview

| Phase | Outcome |
|---|---|
| 0 | Product and solution definition |
| 1 | Architecture decisions and repository foundation |
| 2 | API contract and interface prototype using mock data |
| 3 | Europeana source discovery and corpus policy |
| 4 | Reliable raw-source ingestion |
| 5 | Normalized and validated catalog |
| 6 | Reproducible retrieval documents |
| 7 | Evaluation collection and lexical baseline |
| 8 | Multilingual vector retrieval |
| 9 | Hybrid retrieval and reranking |
| 10 | Grounded generation and deterministic citations |
| 11 | Multilingual optimization and evaluation |
| 12 | Abstention, rights, and prompt-injection protection |
| 13 | Monitoring, hardening, and portfolio release |

---

## Phase 0 — Product and solution definition

### Why

RAG quality cannot be assessed without a defined user, evidence boundary, corpus, and success criteria. Starting with code would hide unresolved product decisions inside implementation details.

### What

- Product goal and target users
- Theme, geography, period, and languages
- MVP and non-MVP scope
- Evidence policy
- Functional and non-functional requirements
- High-level architecture
- Initial quality targets
- Implementation roadmap

### How

- Convert the idea into explicit user journeys.
- Identify what counts as an authoritative source.
- Separate required capabilities from attractive extensions.
- Define measurable outcomes and failure behavior.

### Deliverables

- `SOLUTION_DESIGN.md`
- `IMPLEMENTATION_PHASES.md`

### Learning focus

- Product framing for AI systems
- Evidence boundaries
- Functional versus non-functional requirements
- Why RAG evaluation starts before model selection

### Exit gate

- Solution design reviewed and approved
- Product goal, target users, user journeys, and domain boundary accepted
- MVP, deferred-scope, evidence, and citation boundaries accepted
- Functional requirements, non-functional requirements, architecture, and initial quality targets accepted
- Implementation roadmap accepted
- No unresolved decision that would fundamentally change the architecture

### Status

Complete — Phase 0 scope and roadmap approved on 16 July 2026.

---

## Phase 1 — Architecture decisions and repository foundation

### Why

The project needs reproducible conventions before data and model logic appear. The goal is not a large scaffold; it is a small foundation that makes later choices visible and testable.

### What

- Repository structure
- Python version and dependency-management decision
- Configuration and secret-handling convention
- Testing, linting, and type-checking conventions
- Docker Compose boundary
- Database migration convention
- Architecture decision record template
- Basic continuous-integration checks

### How

1. Write ADRs for consequential choices.
2. Create the smallest package that can be imported and tested.
3. Add deterministic dependency locking.
4. Add quality checks before business logic.
5. Add local infrastructure only after reviewing the Compose design.

### Provisional future structure

```text
lowlands-heritage-rag/
├── docs/
├── src/
├── tests/
├── migrations/
├── data/                 # ignored local data
├── pyproject.toml
├── compose.yaml
└── README.md
```

### Deliverables

- Approved ADRs
- Minimal tested Python package
- Reproducible local dependency environment
- Validated local database service
- Automated quality workflow

### Learning focus

- ADRs and reversibility
- Dependency locking
- Service boundaries
- Liveness versus readiness
- Why infrastructure should follow contracts

### Exit gate

- Clean installation succeeds
- Unit tests, linting, and type checks pass
- Local infrastructure starts and stops predictably
- No credentials are committed

---

## Phase 2 — API contract and interface prototype

### Why

An early interface makes the intended product behaviour visible before data and retrieval decisions become expensive to change. It provides a concrete user journey and stable contracts that later phases can connect to real Europeana data, retrieval, and generation components.

This phase is a prototype boundary. It does not attempt to implement the RAG pipeline before the corpus is understood.

### What

- Local application skeleton
- Versioned API request and response schemas
- Search and answer endpoint contracts
- Synthetic mock cultural-heritage records
- Local interface prototype
- Evidence, citation, provider, source-link, and rights representations
- Loading, empty, error, abstention, and generation-unavailable states
- Placeholder interfaces for retrieval and answer generation
- Contract and interface tests

### How

1. Define the smallest complete user journey.
2. Design API schemas before implementing interface components.
3. Create clearly labelled synthetic records for development.
4. Keep retrieval and generation behind replaceable interfaces.
5. Return mock results through the same contracts intended for real results.
6. Display evidence, providers, source links, rights, and limitations.
7. Test successful, empty, error, and abstention responses.
8. Version contracts when later phases require changes.

### Explicit boundaries

This phase does not include:

- Europeana API access
- Europeana credentials
- Production database integration
- Real ingestion or normalization
- Lexical or vector retrieval
- Embeddings
- Answer-model integration
- Production citation validation
- Claims about the quality or coverage of Europeana data

### Deliverables

- Versioned API contract
- Local application skeleton
- Local interface prototype
- Synthetic test fixtures
- Contract tests
- Prototype user-journey documentation

### Learning focus

- API-first product design
- Contract-driven development
- Dependency boundaries
- Error and uncertainty modelling
- Designing replaceable mock components
- Separating interface behaviour from RAG implementation

### Exit gate

- The local API and interface start successfully
- A mock search journey works end to end
- Request and response contracts are reviewed
- Empty, error, abstention, and unavailable-generation states are visible
- Mock components can be replaced without redesigning the public contract
- No Europeana credentials or production integrations are required

### Status

Complete — Phase 2 contracts, replaceable adapters, deterministic fixtures,
versioned endpoints, static interface, tests, documentation, packaging, and
local browser journey were verified on 17 July 2026.

---

## Phase 3 — Europeana source discovery and sampling

### Why

The proposed Belgian art-and-history corpus is still a hypothesis. Before building production ingestion, we need to understand result volume, Belgian connection metadata, providers, languages, missingness, rights, dates, media types, contemporary coverage, and query noise.

### What

- Europeana API access validation
- Reproducible discovery queries
- Provider and dataset facet report
- Coverage report by decade, language, media type, provider, and rights category
- Small representative sample
- Validation of Belgian connection rules
- Initial Dutch, French, and English topic vocabulary
- Data-contract observations
- Corpus inclusion and exclusion rules

### How

1. Request a Europeana personal API key and configure it securely.
2. Test Search API queries using the preferred `X-Api-Key` authentication header.
3. Query facets before downloading large result sets.
4. Compare providing country with creation place, depicted place, subject, creator, and event metadata.
5. Inspect how object dates, subject dates, digitization dates, and Europeana publication dates differ.
6. Sample across decades from 1900 to the snapshot date, providers, languages, media types, themes, and rights categories.
7. Inspect complete Record API responses for the sample.
8. Document missing, inconsistent, ambiguous, and potentially biased metadata.

### Experiments

- Broad Belgium queries versus named places, artists, events, and movements
- `COUNTRY=belgium` versus explicit Belgian subject or place evidence
- Date and year filters versus dates found only in complete records
- Dutch-, French-, and English-language topic vocabularies
- Images versus text, sound, video, and 3D records
- Openly reusable records versus all rights categories

### Deliverables

- Versioned query configuration
- Data-source exploration and coverage report
- Representative sample of raw records
- Proposed corpus-selection policy
- Europeana response contracts
- Initial multilingual discovery vocabulary

### Learning focus

- API exploration before pipeline construction
- Facets and sampling bias
- Provider geography versus object subject geography
- Metadata completeness and semantic ambiguity
- Data contracts for external sources
- Reproducible corpus boundaries

### Exit gate

- A representative Belgian sample is understood
- Corpus selection rules are approved
- The meaning of Belgian connection and the 1900-to-snapshot period is testable from available metadata
- Expected scale, contemporary coverage, and data-quality risks are documented

---

## Phase 4 — Reliable Bronze ingestion

### Why

A useful ingestion pipeline must be restartable, idempotent, observable, and able to preserve source history. A script that downloads records once is not sufficient.

### What

- Search API client
- Cursor pagination
- Record API client
- Retry and backoff policy
- Rate and concurrency controls
- Immutable compressed raw storage
- Run manifests and checksums
- Incremental-change detection
- Failed-record recovery

### How

1. Model request and response contracts.
2. Separate discovery from record retrieval.
3. Store each raw response before transformation.
4. Calculate content hashes.
5. Record run status and checkpoints.
6. Skip identical previously fetched versions.
7. Retry transient failures but quarantine permanent failures.
8. Test interrupted-run recovery.

### Tests

- Pagination termination
- Duplicate-page protection
- Retry behavior
- Idempotent rerun
- Changed-record version creation
- Corrupt or partial response handling
- Secret redaction

### Deliverables

- Bronze ingestion package
- Raw-data directory convention
- Run manifest
- Ingestion tests
- Operational runbook

### Learning focus

- Idempotency
- Content-addressed version detection
- Backoff and retry budgets
- Checkpointing and replay
- Difference between data errors and transport errors

### Exit gate

- The target sample can be ingested twice without duplication
- An interrupted run resumes correctly
- Every raw record is traceable to a request and run

---

## Phase 5 — Silver normalization and data-quality analysis

### Why

Europeana aggregates heterogeneous institutional metadata. Retrieval quality will be limited by inconsistent languages, dates, places, providers, rights, and missing fields unless these are understood and normalized carefully.

### What

- Canonical object schema
- Multilingual text representation
- Date parsing with uncertainty preservation
- Provider relationships
- Place normalization
- Explicit Belgian connection roles
- Rights taxonomy
- Media-reference normalization
- Source, normalized, and derived value markers
- Data-quality rules and report
- Versioned Silver snapshot

### How

1. Map EDM fields without discarding unmapped source information.
2. Store multilingual values as rows with language codes.
3. Preserve original date strings alongside parsed ranges.
4. Distinguish provider country, creation place, depicted place, subject place, and creator connection.
5. Preserve object dates, subject dates, digitization dates, and Europeana publication dates separately.
6. Normalize rights URIs through an explicit lookup table.
7. Flag suspicious, missing, uncertain, or contradictory values.
8. Write Parquet and load validated current state into PostgreSQL.

### Data-quality dimensions

- Completeness
- Validity
- Consistency
- Uniqueness
- Language coverage
- Temporal coverage
- Provider distribution
- Rights distribution
- Link availability

### Deliverables

- Canonical schema
- Transformation pipeline
- Silver Parquet snapshot
- PostgreSQL catalog schema
- Data-quality report
- Transformation tests
- Belgian connection and temporal-scope validation report

### Learning focus

- Schema-on-read versus schema-on-write
- Lossless normalization
- Slowly changing external records
- Data-quality metrics and bias

### Exit gate

- Transformation is deterministic
- Every normalized object points to a raw version
- Quality failures are measured and categorized

---

## Phase 6 — Gold retrieval-document construction

### Why

Catalog data is optimized for meaning and provenance; retrieval needs a purpose-built text representation. Mixing those concerns makes experiments difficult to reproduce.

### What

- Object-level retrieval-document format
- Language-specific document variants
- Filterable metadata projection
- Content hashes and builder versions
- Rebuild mechanism
- Initial token and length analysis

### How

1. Define which source fields contribute to searchable text.
2. Keep field labels so titles, subjects, dates, and providers retain meaning.
3. Build one source-language representation per object where possible.
4. Mark generated translations as derived data.
5. Store the document recipe and version.
6. Rebuild only documents whose source or recipe changed.

### Deliverables

- Gold document builder
- Retrieval-document schema
- Gold snapshot
- Coverage and length report
- Determinism tests

### Learning focus

- Retrieval units
- Field-aware document construction
- Why metadata objects should not be arbitrarily chunked
- Feature lineage

### Exit gate

- Retrieval documents are reproducible from Silver data
- Each document resolves to exactly one citation object

---

## Phase 7 — Evaluation collection and lexical baseline

### Why

Without relevance judgments, retrieval development becomes subjective. The lexical baseline establishes the minimum system future techniques must beat.

### What

- Multilingual evaluation-question taxonomy
- Relevance judgments
- Train/development/test separation
- Lexical index
- Baseline retrieval runner
- Real lexical-search adapter behind the Phase 2 API contract
- Slice metrics and error analysis

### How

1. Create question categories: lookup, thematic, comparative, filtered, cross-language, rights, and unsupported.
2. Balance English, French, and Dutch.
3. Label relevant objects with graded relevance where useful.
4. Freeze a held-out test set.
5. Implement the simplest transparent lexical search.
6. Record Recall@k, MRR, and nDCG@k.
7. Inspect false positives and false negatives manually.
8. Replace the mock search adapter with the lexical baseline without changing the public API contract.

### Deliverables

- Versioned evaluation dataset
- Annotation guidelines
- Lexical baseline
- API and interface integration for real lexical results
- Baseline report
- Error taxonomy

### Learning focus

- Test-collection design
- Graded relevance
- Dataset leakage
- Macro versus slice metrics
- Why average metrics can hide language failures

### Exit gate

- Evaluation judgments are reviewable
- Baseline run is reproducible
- Major error categories are documented
- The local interface returns real catalog results through the approved contract

---

## Phase 8 — Dense multilingual retrieval

### Why

Dense retrieval may recover conceptually related objects and cross-language matches that exact terms miss. It also introduces model cost, vector indexing, and new failure modes.

### What

- Embedding-model experiment
- Embedding-provider credential setup if an API model is evaluated
- Batched and cached embedding pipeline
- pgvector storage and index
- Dense query retrieval
- Comparison with the lexical baseline
- Cross-language slice analysis

### How

1. Select at least one API and/or local multilingual embedding candidate.
2. Configure credentials securely at this phase if an API embedding model is evaluated.
3. Record model, vector dimension, input recipe, and normalization.
4. Cache using input and configuration hashes.
5. Compare exact and approximate vector search on a controlled sample.
6. Measure dense retrieval on the same held-out judgments.
7. Inspect semantic false positives.

### Deliverables

- Embedding ADR
- Reproducible embedding job
- Vector index
- Dense-baseline report
- Cost, latency, and quality comparison

### Learning focus

- Embedding geometry
- Similarity functions
- Approximate nearest-neighbour search
- Index recall versus latency
- Cross-language semantic retrieval

### Exit gate

- Dense results are reproducible
- Quality and operational trade-offs are measured
- The chosen embedding approach is justified

---

## Phase 9 — Hybrid retrieval and reranking

### Why

Lexical and dense retrieval fail differently. Hybrid retrieval aims to improve recall, while reranking aims to improve top-result precision.

### What

- Reciprocal Rank Fusion baseline
- Candidate-pool analysis
- Multilingual reranker experiment
- Latency and relevance ablations
- Final retrieval configuration

### How

1. Fuse ranked lists using deterministic RRF.
2. Vary lexical and dense candidate depths.
3. Measure gains by language and question type.
4. Add a reranker only to the bounded candidate set.
5. Compare hybrid with and without reranking.
6. Choose the smallest configuration that produces a meaningful gain.

### Deliverables

- Fusion implementation
- Reranker ADR
- Ablation report
- Final retrieval configuration
- Retrieval regression suite

### Learning focus

- Score calibration versus rank fusion
- Candidate recall and reranker precision
- Ablation studies
- Latency-quality Pareto analysis

### Exit gate

- Hybrid and reranking variants are compared on held-out data
- The smallest retrieval configuration that meets the agreed quality target is selected
- Adopted complexity is justified by measured benefit; rejected variants and their reconsideration conditions are documented

---

## Phase 10 — Grounded generation and deterministic citations

### Why

Good retrieval does not guarantee a faithful answer. The generation layer must be constrained by evidence and application-controlled citation logic.

### What

- Generation-model access and credential validation
- Evidence-package contract
- Versioned answer prompt
- Structured answer schema
- Citation validator
- Real answer adapter behind the Phase 2 API contract
- Search-only fallback
- Grounding evaluation

### How

1. Configure or validate generation-model access securely at this phase, reusing an approved credential convention if API embeddings already required one.
2. Build bounded evidence packages from retrieved records.
3. Require object identifiers in structured output.
4. Validate identifiers against supplied evidence.
5. Construct labels and URLs from PostgreSQL.
6. Reject or repair invalid outputs deterministically.
7. Compare answer variants using a fixed retrieval set.
8. Replace the mock answer adapter without changing the public API contract.

### Deliverables

- Generation interface
- Prompt and output-schema versions
- Citation validator
- API and interface integration for grounded answers
- Answer-evaluation set
- Grounding report

### Learning focus

- Context construction
- Structured outputs
- Faithfulness versus fluency
- Citation entailment
- Separating retrieval and generation evaluation

### Exit gate

- Unknown citations cannot reach the user
- Search still works without model access
- Grounding and citation targets are met or failures are documented
- The interface exposes grounded answers, evidence, rights, and generation-unavailable behaviour through the approved contract

---

## Phase 11 — Multilingual optimization and evaluation

### Why

Multilingual support must be measured, not inferred from a model capability statement. Each language and cross-language direction can fail differently.

### What

- Language detection or explicit selection
- Language-aware lexical configuration
- Cross-language dense evaluation
- Answer-language tests
- Historical vocabulary and multilingual spelling analysis
- Per-language error analysis

### How

1. Separate retrieval language from response language.
2. Measure same-language and cross-language retrieval.
3. Preserve the original query and detected or selected language.
4. Evaluate cultural names, spelling variants, and historical vocabulary.
5. Report metrics separately for English, French, and Dutch.
6. Record translation or expansion as a post-MVP recommendation only if the measured errors justify a later experiment.

### Deliverables

- Multilingual test matrix
- Language-routing policy
- Per-language quality report
- Post-MVP recommendation for translation or expansion if justified

### Learning focus

- Cross-lingual information retrieval
- Translation drift
- Language imbalance
- Slice-based evaluation

### Exit gate

- All three languages meet agreed minimum quality
- Cross-language weaknesses are explicit and monitored

---

## Phase 12 — Abstention, rights, and prompt-injection protection

### Why

A production RAG system must know when not to answer, respect reuse conditions, and treat retrieved content as untrusted.

### What

- Supported and unsupported question set
- Evidence-sufficiency features
- Calibrated abstention policy
- Rights filters and display rules
- Malicious-record fixtures
- Prompt-injection and citation attacks
- Security regression suite

### How

1. Create unsupported, ambiguous, and contradictory questions.
2. Calibrate thresholds using development data.
3. Keep rights logic deterministic and outside the model.
4. Delimit evidence structurally.
5. Test instructions embedded inside retrieved metadata.
6. Test fabricated identifiers, URLs, and rights claims.
7. Measure both unsafe answering and excessive refusal.

### Deliverables

- Abstention policy
- Rights taxonomy and filter behavior
- Threat model
- Adversarial test suite
- Security and abstention report

### Learning focus

- Selective prediction
- Threshold calibration
- Prompt-injection trust boundaries
- Deterministic policy enforcement

### Exit gate

- Rights claims come only from normalized source data
- Injection tests cannot override system behavior
- Abstention performance meets the agreed target

---

## Phase 13 — Monitoring, hardening, and portfolio release

### Why

Production readiness includes diagnosis, recovery, reproducibility, and communication. A portfolio repository must show not only that the happy path works, but how failures and trade-offs are handled.

### What

- Structured application logs
- Retrieval and answer traces
- Local dashboards or reports
- Data and retrieval drift checks
- Failure taxonomy and runbooks
- Performance profiling
- Reproducible demonstration dataset
- Architecture and experiment summaries
- Final README and release checklist

### How

1. Define operational signals from known failure modes.
2. Record component latency and dependency failures.
3. Monitor corpus composition and missingness between ingestion versions.
4. Run the full regression suite from a clean environment.
5. Document key experiments, rejected alternatives, and limitations.
6. Prepare concise example questions with traceable outputs.

### Deliverables

- Monitoring and diagnostic views
- Operational runbook
- Clean-install verification
- Portfolio-quality README
- Architecture diagram
- Evaluation report
- End-to-end user guide
- Versioned local release

### Learning focus

- Observability versus logging
- Data and model drift
- Incident diagnosis
- Performance budgets
- Communicating engineering evidence

### Exit gate

- Clean local setup is reproducible
- Failures can be detected and diagnosed
- Results and limitations are documented honestly
- A new user can complete the search, answer, evidence, rights, and abstention journey locally
- A technical reviewer can understand the decisions and evidence

## 4. Suggested learning cadence

Within every implementation phase:

1. **Concept briefing** — understand the technique and its failure mode.
2. **Minimal baseline** — build the simplest measurable version.
3. **Inspect examples** — examine successes and failures manually.
4. **Form a hypothesis** — state why a change should help.
5. **Run an experiment** — change one meaningful factor.
6. **Measure** — compare with the preserved baseline.
7. **Decide** — accept, reject, or defer the change.
8. **Document** — record the result and conditions for reconsideration.

This cadence provides speed without turning the project into an untraceable collection of tools and prompts.
