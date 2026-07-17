# ADR 0003 and Phase 3 master record

- Status: Proposed pending corpus-policy approval
- Date: 2026-07-17
- Scope: Europeana source discovery and corpus-policy validation
- Role: Single source of truth for Phase 3

## 1. Outcome

Phase 3 implementation, bounded live research, analysis, and technical exit
checks are complete. Europeana can support a useful Belgian cultural-heritage
corpus, but only through explicit record-level policy. A broad country query is
too ambiguous, concentrated, and image-heavy to define the corpus.

Phase 4 has not started. The remaining governance gate is explicit approval of
the proposed corpus-selection rules in this record.

## 2. Boundary

Phase 3:

- uses Search for counts, facets, and candidates;
- uses Record for complete metadata inspection;
- preserves the Phase 2 API, interface, and synthetic adapters;
- makes sequential, bounded requests only;
- downloads no media and ingests no corpus;
- keeps raw redacted samples under ignored `data/`;
- keeps ordinary tests and CI credential-free.

## 3. Architecture

```text
discovery_queries_v1.toml
        |
        v
query_matrix.py -> exploration.py -> EuropeanaDiscoveryClient
                                         |
                                         v
                                HttpTransport protocol
                                         ^
                                         |
                                Httpx2Transport adapter
```

Key components:

| Component | Responsibility |
| --- | --- |
| `configuration.py` | Load and redact the application-owned credential |
| `query_matrix.py` | Validate versioned hypotheses, categories, languages, and bounds |
| `contracts.py` | Validate provider JSON separately from project summaries |
| `transport.py` | Define the library-independent HTTP port |
| `httpx2_transport.py` | Apply explicit timeouts and one-connection limits |
| `client.py` | Build fixed-endpoint requests, authenticate, parse, redact, and classify errors |
| `exploration.py` | Execute the matrix sequentially and create bounded summaries |
| `run_live.py` | Write one non-overwriting aggregate/redacted local snapshot |

The client depends on the transport protocol rather than HTTPX2 directly. This
keeps request behavior testable with fake transports and preserves the
ports-and-adapters architecture.

## 4. API and security facts

- Search endpoint: `https://api.europeana.eu/record/v2/search.json`
- Record endpoint: `https://api.europeana.eu/record/v2/{dataset}/{local}.json`
- Authentication: `X-Api-Key` header
- Local variable: `LOWLANDS_LENS_EUROPEANA_API_KEY`
- Deprecated `wskey` query authentication is unsupported.
- Successful Search and Record responses returned HTTP 200 JSON.
- Search `edmIsShownAt` and `edmPreview` were observed as lists.
- Record proxy `edmType` was observed as a scalar string.

Critical finding: Europeana returned an `apikey` response field equal to the
real header credential. Therefore:

- raw responses must never be printed or logged;
- exceptions must not include bodies, headers, URLs, or validation inputs;
- stored raw samples must recursively redact `apikey`, `X-Api-Key`, and
  `wskey`;
- raw data remains ignored and must pass a tracked-secret scan.

## 5. Method and bounds

The authoritative snapshot used query-matrix schema version 1 on 2026-07-17:

- 13 sequential Search requests;
- 12 items per normal query and 20 for the noisy baseline;
- six sequential Record requests;
- no retries, concurrency, cursor traversal, checkpointing, or media download;
- English, French, and Dutch queries across 11 categories;
- six Record strata covering places, art, war memory, colonial history, and
  mixed media.

Tracked aggregate evidence:
`config/phase3/discovery_observations_2026-07-17.toml`.

Ignored local evidence:
`data/phase3/2026-07-17-v2/`.

## 6. Essential findings

### Query volumes

| Query | Results |
| --- | ---: |
| Belgian cities — English | 29,872 |
| Belgian cities — French | 17,049 |
| Belgian cities — Dutch | 20,374 |
| Magritte / surrealism | 8 |
| Art Nouveau Brussels + image | 0 |
| First World War remembrance | 11 |
| Belgian Congo colonial history | 1 |
| Migration and social change | 0 |
| Design, posters, photography + image | 0 |
| Film, radio, literature | 3 |
| Open-reusability heritage | 453 |
| Contemporary Belgian culture | 0 |
| Broad `Belgium` baseline | 633,040 |

Zero results show query behavior, not source absence. Combined abstract terms,
language, parser behavior, and refinements can create false negatives.

### Broad-baseline distribution

| Dimension | Observation |
| --- | --- |
| Provider | OpenUp! 53.6% |
| Data provider | Meise Botanic Garden 50.9% |
| Country | Belgium 90.7% |
| Language | `mul` 56.0%; French 20.9%; English 19.5%; Dutch 0.8% |
| Media | Image 87.4%; text 11.7%; video 0.8%; sound 0.1% |
| Reusability | Open 61.2%; restricted 23.8%; permission 15.0% |

Facet counts are dated query observations, not cultural importance, recall, or
legal conclusions. Filtered facets can show alternative refinement values, so
their sums need not equal the filtered result total.

### Multilingual behavior

| City names | Results | Top provider | Requested-language metadata |
| --- | ---: | ---: | ---: |
| English | 29,872 | 54.4% | 2.3% `en` |
| French | 17,049 | 55.2% | 13.9% `fr` |
| Dutch | 20,374 | 48.1% | 3.9% `nl` |

Language-specific names changed coverage and provider composition but did not
make returned metadata predominantly that language. Preserve every source
language map, including `def` and `mul`; do not silently translate or expand.

### Record sample

| Signal | Present |
| --- | ---: |
| Titles | 6 / 6 |
| Descriptions | 4 / 6 |
| Dates | 6 / 6 |
| Subjects | 5 / 6 |
| Creators | 4 / 6 |
| Explicit places | 3 / 6 |
| Source links | 6 / 6 |
| Aggregation-level object rights | 6 / 6 |
| Web resources with their own rights | 0 / 17 |

Search is sufficient for counts/facets/candidates. Record adds multilingual
descriptions, subjects, creators, spatial fields, date roles, aggregations, and
web resources required for normalization and relevance review.

### Belgian connection sample

Five records had explicit Belgian title, subject, description, or spatial
evidence and were classified `include`. The Magritte record remained
`manual_review`: its title names Magritte, but the sampled metadata did not
itself state the Belgian relationship.

Provider or data-provider location is never sufficient subject evidence.
Relevant Belgian records may be held by institutions outside Belgium.

## 7. Decisions

1. Use only Search and Record during bounded discovery.
2. Use `X-Api-Key` through injected, representation-safe credentials.
3. Keep a versioned TOML query matrix marked `phase_3_exploration_only`.
4. Model dedicated parameters such as `reusability` separately from generic
   `qf` refinements.
5. Keep provider payloads separate from strict internal summaries and the
   future canonical catalog.
6. Use a synchronous transport port with HTTPX2, explicit timeouts, one
   connection, no redirects, and no global mutable client.
7. Execute sequentially without retries, concurrency, or harvesting.
8. Track aggregates; keep complete redacted samples ignored locally.
9. Require explicit Belgian metadata evidence; provider country is only a
   candidate signal.
10. Keep date roles, language maps, metadata rights, aggregation rights, and
    web-resource rights separate.

Rejected alternatives include a broad `Belgium` corpus, `COUNTRY=Belgium` as
relevance, Search summaries as complete records, raw response logging,
automatic provider exclusion, premature harvesting infrastructure, and early
flattening of languages/dates/rights.

## 8. Proposed corpus-selection policy

### Include

A future normalized record is eligible when it has:

- stable Europeana ID and complete Record snapshot;
- at least one title;
- provider or data-provider attribution;
- at least one retained source link;
- explicit Belgian subject/place/event/person/institution/culture evidence;
- an applicable cultural-object date from 1900-01-01 through the snapshot date,
  or an approved review decision;
- separate metadata- and digital-object-rights states.

### Exclude

Exclude when:

- provider location or query match is the only Belgian signal;
- the object is certainly before 1900;
- only digitization/update/publication metadata places it in range;
- mandatory identity/title/attribution/link/Record evidence is missing;
- it is an obvious false positive or deleted record.

No provider or dataset is globally excluded from Phase 3 evidence alone.

### Review or quarantine

Use `include`, `exclude`, `ambiguous`, and `manual_review`. Keep ambiguous or
manual-review records outside the searchable corpus until resolved. Person or
institution connections require explicit metadata or an approved authority
mapping.

### Time, media, language, and rights

- Keep creation, issue, subject-event, digitization, provider-record, and
  Europeana dates separate.
- Quarantine conflicting, boundary, or unsupported dates; do not use
  digitization/update dates as object dates.
- Keep image, text, sound, video, and 3D metadata eligible while countering
  image dominance in sampling/evaluation.
- Preserve all original language values; never flatten `mul` or translate
  silently.
- Treat Europeana metadata CC0 policy separately from linked-object rights.
- Missing web-resource rights never imply permission.
- Retain every raw record and provenance before any later duplicate clustering;
  never destructively merge source records.

The 633,040-result baseline is not an approved ingestion target. Phase 4 needs
a reviewed maximum scale and dataset-aware acquisition plan.

## 9. Operation

Credential-free checks:

```powershell
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv build
```

Explicitly approved bounded live snapshot:

```powershell
uv run --locked --env-file .env python -m lowlands_lens.discovery.run_live --matrix config/phase3/discovery_queries_v1.toml --output-dir data/phase3/YYYY-MM-DD --snapshot-date YYYY-MM-DD
```

The live command refuses to overwrite existing snapshot files, prints no raw
metadata, and writes only under ignored `data/`.

## 10. Verification

- Locked sync passed.
- 71 credential-free tests passed.
- Ruff lint and formatting passed.
- Strict mypy passed.
- Source distribution and wheel built successfully.
- All discovery modules were present in the wheel.
- Final one-row live Search smoke test passed.
- Search and Record header authentication passed.
- Zero tracked credential matches were found.
- `.env` and local raw snapshots were confirmed ignored.
- No Phase 2 public contract or adapter was replaced.

## 11. Limitations and Phase 4 risks

Thirteen queries and six records cannot prove recall, cultural
representativeness, legal reuse, population-level missingness, historical
accuracy, or final corpus size. Provider concentration, rank bias, incomplete
language labels, ambiguous date roles, query false negatives, missing web
rights, and duplicate manifestations remain material risks.

Phase 4 must add immutable Bronze storage, provenance, pagination,
checkpointing, rate handling, bounded scale, and failure recovery only after
this policy is approved. Bulk needs should trigger reassessment of Dataset
Download or OAI-PMH instead of indiscriminate Search traversal.

## 12. Approval gate

Approval means accepting the proposed record-level corpus boundary above. It
does not approve a large download, media acquisition, production integration,
or Phase 4 implementation.

To close Phase 3, reply:

```text
I approve the proposed Phase 3 corpus-selection policy.
```

After approval, change this record to `Accepted` and mark the final roadmap
checkbox complete.

## References

- [Phase 3 query matrix](../../config/phase3/discovery_queries_v1.toml)
- [Phase 3 aggregate observations](../../config/phase3/discovery_observations_2026-07-17.toml)
- [Implementation roadmap](../IMPLEMENTATION_PHASES.md)
- [README](../../README.md)
- [Europeana API overview](https://pro.europeana.eu/page/apis)
- [Search API documentation](https://europeana.atlassian.net/wiki/spaces/EF/pages/2385739812/Search)
- [Record API documentation](https://europeana.atlassian.net/wiki/spaces/EF/pages/2385674279/Record%2BAPI%2BDocumentation)
- [Europeana fair-use policy](https://europeana.atlassian.net/wiki/spaces/EF/pages/2704146433)
- [Europeana metadata usage guidelines](https://www.europeana.eu/eu/rights/usage-guidelines-for-metadata)
