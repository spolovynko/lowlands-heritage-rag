# Phase 3 Europeana API documentation lesson

- Documentation checked: 17 July 2026
- Scope: official documentation review only
- Live API requests made: none
- Credentials used or inspected: none

## Purpose

This note records the documented Europeana interfaces that Phase 3 can use for
bounded source discovery. It separates Europeana's published behavior from
Lowlands Lens design inferences. Behavior that cannot be established from
documentation remains an explicit live-validation question.

## How to find the official documentation

1. Open the [Europeana API overview](https://pro.europeana.eu/page/apis).
2. Under **Explore our APIs**, select **Accessing the APIs** for credentials and
   access policy.
3. Return to the API overview and select **Search API** for discovery, facets,
   profiles, refinements, and pagination.
4. Return again and select **Record API** for complete metadata about one item.
5. Open the [Europeana Terms and Policies](https://www.europeana.eu/en/rights),
   then select **Terms of Use** and **Usage Guidelines for Metadata**.
6. For digital-object rights vocabulary, open **Understanding the rights
   statements used by Europeana** from the Europeana Pro copyright pages.

Europeana Pro now points API readers to the Europeana Knowledge Base. The
Knowledge Base pages are therefore the current detailed interface reference;
Europeana Pro remains the official navigation entry point.

## Available interfaces

The official overview currently lists Search, Record, Entity, Annotations,
IIIF, SPARQL, Dataset Download and OAI-PMH, Thumbnail, Recommendation, and User
Set APIs.

Lowlands Lens Phase 3 needs only two:

- **Search API** to discover records, compare queries, count results, request
  facets, and collect candidate Europeana identifiers.
- **Record API** to inspect the complete EDM metadata for a small, bounded
  sample of identified records.

The other interfaces are outside the approved Phase 3 boundary. Europeana's
fair-use guidance recommends Dataset Download or OAI-PMH when a use case needs
metadata in bulk, but Phase 3 is not a bulk-download phase.

## Search API: documented behavior

### Endpoint and role

```text
GET https://api.europeana.eu/record/v2/search.json
```

The Search API searches Europeana's indexed metadata and media information. A
`query` is required. Authentication is also required for this API, with the
documented exceptions applying to other API families rather than Search.

Search results are summaries. They are useful for corpus measurement and
candidate selection, but they are not a substitute for complete Record API
metadata.

### Important request parameters

| Parameter | Documented purpose |
| --- | --- |
| `query` | Required search expression. |
| `qf` | Repeatable query refinement. |
| `reusability` | Filter using `open`, `restricted`, or `permission`. |
| `media` | Require a resolvable full-media URL. |
| `thumbnail` | Require an available generated thumbnail. |
| `landingpage` | Require a verified provider landing page. |
| `theme` | Restrict to a documented Europeana thematic collection. |
| `sort` | Sort by supported fields or use a random order, optionally seeded. |
| `profile` | Control returned metadata and additional response structures. |
| `rows` | Number of items; default 12 and documented maximum 100. |
| `start` | One-based offset for basic pagination; default 1. |
| `cursor` | Cursor mark for deep pagination; start with `*`. |
| `facet` | Select one or more facet fields. |

The query syntax supports basic and phrase search, fielded search, Boolean
operators, wildcards, fuzzy terms, and ranges. Europeana documents Lucene query
syntax with Solr eDisMax as the default query parser.

### Profiles and facets

Documented profiles include:

- `minimal`, `standard`, and `rich` metadata sets;
- `facets` to add facet information using the standard record profile;
- `breadcrumbs` to add query breadcrumbs and facets;
- `params` to return requested and default request parameters;
- `portal`, which combines the portal-oriented response elements.

Facets are requested with `profile=facets`. The `facet` parameter can name one
field, be repeated, or contain a comma-separated list. `DEFAULT` is a shortcut
for the default facet set. Per-facet limit and offset parameters are documented
as `f.[FACET_NAME].facet.limit` and `f.[FACET_NAME].facet.offset`.

The documented default facet set includes fields useful to Phase 3, including
`TYPE`, `LANGUAGE`, `COMPLETENESS`, `COUNTRY`, `DATA_PROVIDER`, `PROVIDER`,
`RIGHTS`, `YEAR`, `MIME_TYPE`, `REUSABILITY`, `LANDINGPAGE`, `MEDIA`, and
`THUMBNAIL`, plus other technical-media fields. Europeana's fair-use guidance
specifically recommends faceting on `edm_datasetName` to identify datasets
before considering bulk-access mechanisms.

A facet response contains a facet name and values composed of a label and
record count. These counts describe the current result set for the submitted
query; they are not evidence of historical importance or representativeness.

### Pagination

Europeana documents two pagination modes:

- **Basic pagination** uses `start` and `rows`, permits navigation to a chosen
  offset, and is limited to the first 1,000 results when `start + rows` is
  considered.
- **Cursor pagination** starts with `cursor=*`, uses the response's
  `nextCursor` value for the next request, cannot jump to an arbitrary offset,
  and cannot be combined with `start`. Pagination ends when `nextCursor` is no
  longer returned.

Discovery should normally prefer counts and facets. Cursor traversal belongs
to Phase 4 production ingestion, not Phase 3 exploration.

### Response and error shape

Documented Search response fields include `success`, `statsDuration`,
`requestNumber`, `itemsCount`, `totalResults`, `nextCursor`, `items`, `facets`,
and `breadcrumbs`, depending on the request profile.

Documented error status codes include:

- `401` for missing or failed authentication;
- `429` when the application's usage limit has been reached;
- `500` for an unhandled server error.

The documentation also describes an `apikey` response field. Whether a key
sent through the preferred header is echoed in this field must be validated
before any raw response is stored or displayed.

## Record API: documented behavior

### Endpoint and identifier

```text
GET https://api.europeana.eu/record/v2/{DATASET_ID}/{LOCAL_ID}.json
```

A Europeana record identifier contains a dataset identifier and a local
identifier in the form `/DATASET_ID/LOCAL_ID`. The Search API's record ID is
therefore the bridge to the Record API path.

The primary Record API output is Europeana-specific JSON representing EDM.
The documentation also describes JSON-LD and RDF/XML serializations. Its prose
and extension table are not fully consistent about the JSON-LD extension, so
Phase 3 will use only the primary `.json` format unless a later requirement
justifies validating another serialization.

### Response and errors

The complete record is returned under the top-level `object` field. The
documented response also includes request-handling fields such as `success`,
`statsDuration`, and `requestNumber`.

Documented error status codes include:

- `401` for missing or failed authentication;
- `404` when the record does not exist;
- `429` when the application reaches its usage limit;
- `500` for an unhandled server error.

Like Search, the Record documentation includes an `apikey` response field, so
redaction must cover response bodies as well as request headers, URLs, logs,
exceptions, fixtures, and reports.

## Authentication and access policy

Since 28 May 2025, Europeana distinguishes Personal and Project API keys.

- A **Personal key** is intended for experimentation, discovery, and
  non-production individual use. One active Personal key is allowed per user.
- A **Project key** is intended for production services or operational use at
  scale and has higher usage limits. Europeana recommends testing with a
  Personal key first.

To obtain a Personal key yourself later:

1. Open [Europeana](https://www.europeana.eu/en).
2. Select **Log in / Join** in the upper-right corner.
3. Create an account or sign in and verify the account if prompted.
4. Open the upper-right menu beside your nickname.
5. Select **Manage API keys**.
6. In **Personal API key**, read and accept the API-key terms.
7. Select **Request a Personal API key**.

Do not perform those steps during this documentation lesson unless you want to
prepare for Step 3. Never paste the resulting value into chat, source code,
documentation, an issue, or a command that will print it.

For read-only public access, the preferred authentication method is:

```text
X-Api-Key: [local secret value]
```

Lowlands Lens stores that local secret under one application-owned environment
variable name:

```text
LOWLANDS_LENS_EUROPEANA_API_KEY=
```

The tracked `.env.example` contains only this empty placeholder. A developer
places the real value after `=` in the ignored `.env`. The value must never be
copied into documentation, source code, tests, reports, logs, URLs, or chat.

The older `wskey` URL parameter is deprecated. Lowlands Lens will not use it,
because credentials in URLs can leak through history, bookmarks, logs, error
messages, monitoring, and shared links.

## Fair use and rate guidance

The official pages do not publish a single numeric request or concurrency
limit for Personal keys. They state that Personal-key limits were progressively
reduced through April 2026, Project keys have higher limits, and Europeana may
change reasonable limits to protect service performance.

The fair-use policy requires reasonable concurrency and a wait for requests to
complete. On a limit error, clients must lower concurrency and usage. Repeated
excessive use may result in temporary blocking or key revocation. Europeana
recommends Dataset Download or OAI-PMH instead of repeated item requests for
large-scale metadata access.

Lowlands Lens inference: Phase 3 should use sequential, strictly bounded calls,
small `rows` values, facets before item retrieval, and no automatic concurrency.
This is a conservative project policy, not a numeric limit published by
Europeana.

## Metadata and digital-object rights

Official Europeana policy distinguishes metadata from linked digital objects:

- Europeana metadata is published under CC0. Europeana nevertheless requests
  attribution to the data provider, contributing aggregators, and Europeana,
  with source and rights links retained where possible.
- Metadata is dynamic and can be corrected or enriched over time. A snapshot
  therefore needs a date, request configuration, and provenance.
- Digital objects and thumbnails are governed by the rights statement recorded
  for the object and by applicable law. CC0 metadata does not make the linked
  object freely reusable.
- If object rights are absent, the user must not infer permission. Europeana's
  terms direct users to applicable copyright law and the provider site.
- Europeana documents 14 standardized digital-object rights statements drawn
  from Creative Commons licenses and tools and RightsStatements.org.

These facts support the existing Phase 2 decision to keep metadata rights and
digital-object rights separate.

## Official facts and Lowlands Lens inferences

| Officially documented fact | Project inference to test or adopt |
| --- | --- |
| Search returns result summaries, counts, and optional facets. | Use it to measure possible corpus shape, not as final answer evidence. |
| Record returns complete EDM metadata for one Europeana ID. | Inspect only a stratified bounded sample during Phase 3. |
| `COUNTRY` is available as a search field/facet. | Do not treat provider country as proof that an object is about Belgium. |
| Facet counts describe matching indexed records. | Counts reveal concentration and missingness, not cultural importance. |
| Metadata can change. | Every report needs a snapshot date and reproducible request configuration. |
| `X-Api-Key` is preferred and `wskey` is deprecated. | Reject query-string authentication in all project code and tests. |
| No fixed public numeric Personal-key limit is stated. | Keep Phase 3 sequential and bounded until live behavior is measured. |
| Search has cursor pagination for the full result set. | Do not build harvesting infrastructure before Phase 4. |

## Why discovery precedes ingestion

An ingestion pipeline encodes assumptions about what to download, how much to
download, how to resume, and which records belong in the corpus. Those choices
would be premature while provider concentration, languages, dates, media,
rights, missingness, query noise, and Belgian relevance are unmeasured.

Phase 3 therefore uses cheap aggregate evidence first: query counts and facets.
It then inspects a deliberately small Record API sample. Only after the corpus
policy is approved can Phase 4 design reliable pagination, retry, checkpoint,
and raw-storage behavior for a known boundary.

## Questions requiring bounded live validation

1. Does `X-Api-Key` work consistently for both Search and Record endpoints?
2. Does either endpoint echo the real header key in the `apikey` response field?
3. What `Content-Type` is returned for successful and error JSON responses?
4. Are authentication failures always `401`, or can `403` occur?
5. What body and headers accompany `429`, including any retry guidance?
6. Are `totalResults` and facet counts exact for the tested queries?
7. Is `rows=0` accepted consistently for facet-only requests?
8. Are repeated `qf` and `facet` parameters preserved and interpreted as
   documented?
9. Which documented facets are actually returned for the approved queries?
10. Does cursor pagination terminate exactly when `nextCursor` disappears?
11. How must unusual local identifiers be percent-encoded in Record paths?
12. Which multilingual, rights, provider, date, place, and source-link fields
    are consistently present in real Search summaries and Record payloads?
13. What current practical request limit applies to the configured Personal key?

These questions are observations to collect later, not permission to make live
requests during this step.

## Official sources checked

- [Europeana APIs overview](https://pro.europeana.eu/page/apis)
- [Accessing the APIs](https://europeana.atlassian.net/wiki/spaces/EF/pages/2462351393/Accessing%2Bthe%2BAPIs)
- [Search API documentation](https://europeana.atlassian.net/wiki/spaces/EF/pages/2385739812/Search)
- [Record API documentation](https://europeana.atlassian.net/wiki/spaces/EF/pages/2385674279/Record%2BAPI%2BDocumentation)
- [Fair use policy and guidelines](https://europeana.atlassian.net/wiki/spaces/EF/pages/2704146433)
- [Europeana Terms of Use](https://www.europeana.eu/en/rights/terms-of-use)
- [Usage Guidelines for Metadata](https://www.europeana.eu/eu/rights/usage-guidelines-for-metadata)
- [Understanding the rights statements used by Europeana](https://pro.europeana.eu/page/available-rights-statements)
