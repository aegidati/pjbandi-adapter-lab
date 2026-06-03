# incentivi_gov - Incentivi.gov.it

## Source overview

| Field | Value |
|---|---|
| Source ID | incentivi_gov |
| Source name | Incentivi.gov.it |
| Entry URL | https://www.incentivi.gov.it/it/catalogo |
| Solr endpoint | https://www.incentivi.gov.it/solr/coredrupal/select |
| Source type | catalog_html (JS/Solr-backed) |
| Adapter status | TESTING |
| Pattern adapter | CatalogHtmlAdapter + source-specific Solr discovery |

## Adapter strategy

The catalog page is rendered client-side and does not contain incentive cards in static HTML.
The adapter therefore:

1. Reads service-config from the catalog page.
2. Calls Solr endpoint for docs discovery.
3. Maps Solr docs to RawCandidate.
4. Fetches detail page HTML as primary evidence.
5. Persists Solr doc as secondary JSON evidence.
6. Uses Solr fields as source-of-truth in extract when available.

## Solr to canonical mapping

### RawCandidate mapping

| Canonical field | Primary aliases | Fallback aliases | Notes |
|---|---|---|---|
| id | derived from candidate URL | derived from solr_doc_id only if URL unavailable | Uses short_id(url). |
| url | url, link, permalink | path, path_alias, alias, view_node, generic keys containing url/path | URL is normalized against catalog base URL. |
| title | title, titolo | name, subject, generic keys containing title/titolo | Optional, but preferred. |
| metadata.solr_doc_id | id | - | Stored for traceability. |
| metadata.solr_doc | full doc payload | - | Stored for later extract mapping. |
| metadata.solr_url | query URL used | - | Useful for runtime diagnostics. |

### ExtractionResult mapping

| Canonical field | Primary aliases | Fallback behavior | Source of truth |
|---|---|---|---|
| title | title, titolo | name, subject, HTML title fallback | solr when present |
| publication_date | publication_date, data_pubblicazione, published_at, published, created | key scan containing pubblic or created | solr when present |
| deadline | deadline, data_scadenza, scadenza, termine_presentazione | key scan containing scaden or termine | solr when present |
| attachment_urls | attachment_urls, attachments, allegati, files, documenti | mapping from nested object keys: url, href, link | html plus solr |
| raw_fields.solr_doc | full Solr doc | - | always when JSON asset exists |
| raw_fields.source_of_truth | title/publication_date/deadline/attachment_urls | - | explicit provenance per field |

### Source-specific extraction status rule

For incentivi_gov, extraction status is evaluated with source-specific semantics:

1. failed: title missing
2. success: title present and at least one among deadline, publication_date, attachment_urls
3. partial: title present but no deadline/publication_date/attachments

This avoids penalizing records where deadline is not published by the source but the extraction remains usable.

## Normalization rules

1. URLs are normalized to absolute URLs using source base URL.
2. Dates are normalized to YYYY-MM-DD.
3. Existing ISO-like values keep first 10 chars.
4. Italian textual or numeric dates are parsed via normalize_italian_date.
5. Attachment URLs are deduplicated preserving order.
6. Technical Solr endpoint URLs are excluded from attachment_urls output.

## Discovery filters

The adapter excludes non-detail paths from discovered candidates:

- /it
- /it/catalogo
- /it/chi-siamo
- /it/faq
- /it/glossario
- /it/open-data
- /it/privacy
- /it/note-legali
- /it/accessibilita
- /it/scrivania*

Accepted detail paths include:

- /it/catalogo/*
- paths containing: incentiv, misura, agevolaz, bando, scheda

## Safety and performance

1. Solr rows are bounded with a hard cap (300) to avoid over-fetching.
2. Discovery falls back to static HTML filtering only when Solr call/parsing fails.
3. Static fallback is restricted to detail-like paths only.

## Tests

Current coverage includes:

- discover from Solr docs
- filtering non-detail paths
- rows cap behavior
- static fallback on invalid Solr response
- fetch adds Solr JSON evidence asset
- extract prefers Solr fields for canonical output
- integration pipeline from Solr fixture

## Source-specific validation thresholds

Validation keeps default global checks, with incentivi_gov-specific thresholds for two metrics
to reflect source characteristics:

- pdf_presence: threshold 3% (global default is 20%)
- deadline_completeness: threshold 30% (global default is 50%)

Rationale:

1. many incentivi cards do not expose a direct downloadable PDF from the detail page
2. many cards do not publish an explicit deadline, especially for evergreen or informational measures

## Known limitations

1. Solr schema can evolve; aliases may need periodic updates.
2. Deadline may be absent for many records and remains null when not explicit.
3. Some domain fields are currently retained in raw_fields but not promoted to semantic_fields.

## TODO

- DONE: expand Solr deadline alias mapping with field samples collected from fresh payload snapshots.
- DONE: add a source-specific deadline fallback from HTML blocks (when explicit in detail page and absent in Solr doc).
- TODO: track deadline coverage by bucket (national, regional, local issuers) to understand low-completeness drivers.

## Promotion decision

Current promotion level: TESTING.

Promotion rationale:

1. adapter passes source-specific validate checks with `Passed: True`
2. extraction completeness reaches 100% under the current source-specific rule
3. known residual risk is operational (source variability), not a blocking code defect

## Promotion checklist

1. Validate field aliases on fresh Solr snapshots.
2. Add fixture variants for nested attachment structures.
3. Add coverage for additional date formats if found in production docs.
4. Run full validate command and baseline quality metrics for incentivi_gov.
