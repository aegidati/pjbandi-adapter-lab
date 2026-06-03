# invitalia - Incentivi e Strumenti

## Source overview

| Field | Value |
|---|---|
| Source ID | invitalia |
| Source name | Invitalia Incentivi e Strumenti |
| Entry URL | https://www.invitalia.it/per-le-imprese/incentivi-e-strumenti |
| Source type | catalog_html |
| Adapter status | TESTING |
| Pattern adapter | CatalogHtmlAdapter + source-specific paginated discovery |

## Adapter strategy

1. Try direct API discovery from endpoints referenced in page scripts.
2. If no direct API candidates are found, discover paginated listing pages with `?page=N`.
3. In paginated mode, use JSON scripts first and fallback to HTML anchors.
4. Fetch detail HTML and linked evidence assets (PDF/DOC/DOCX/ZIP).
5. Extract deterministic fields from detail content with label-aware date parsing.

## URL and pagination rules

Accepted detail URLs:

- `/incentivi-e-strumenti/*`

Excluded listing URL:

- `/per-le-imprese/incentivi-e-strumenti`

Canonicalization rules:

1. normalize URL to absolute on `https://www.invitalia.it`
2. remove fragment
3. drop query parameter `from` for dedup stability
4. clean noisy listing titles by removing boilerplate prefixes/suffixes

Title cleanup rules:

1. remove prefix `Leggi tutto su`
2. remove trailing status markers like `ATTIVO`, `IN APERTURA`, `CHIUSO`, `SOSPESO`
3. normalize whitespace

Pagination behavior:

1. start from `page=0`
2. continue while a link to `page=N+1` exists
3. safety guardrail: max 30 pages
4. stop early when a page after the first yields no new candidates

## Deterministic extraction rules

From detail HTML:

1. title from first visible `h1`
2. publication_date from `Data apertura` label
3. deadline from `Data chiusura` label
4. attachment_urls from linked documents in detail page

Status semantics:

1. failed: title missing
2. success: title and at least one among deadline, publication_date, attachments
3. partial: title present but no other key fields

## Known limitations

1. Embedded JSON structure can vary between releases.
2. Direct API discovery is currently script-derived; no stable hardcoded public endpoint has been confirmed.
3. Deadline may be absent for evergreen initiatives.

## TODO

- DONE: add direct API discovery branch using script-derived endpoints with safe fallback.
- TODO: add fixture for inactive/closed incentives and verify status-specific extraction behavior.
- DONE: validate baseline captured (candidate_count 104, fetch_coverage 1.00, pdf_presence 0.42, title_completeness 1.00, deadline_completeness 0.72, extraction_completeness 0.96); keep global thresholds for now.
