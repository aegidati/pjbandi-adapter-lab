# veneto_bandi — Bandi Regione Veneto

## Source overview

| Field | Value |
|---|---|
| Source ID | `veneto_bandi` |
| Source name | Bandi Regione Veneto |
| Entry URL | https://bandi.regione.veneto.it/Public/Index |
| Listing URL | https://bandi.regione.veneto.it/Public/Elenco |
| Source type | `regional_html_pdf` |
| Adapter status | `TESTING` |
| Pattern adapter | `RegionalHtmlPdfAdapter` |

## Adapter strategy

The adapter extends `RegionalHtmlPdfAdapter`, which handles HTML detail pages with
linked PDF attachments. Source-specific logic is layered on top for discovery URL
filtering and optional authority extraction.

## Discovery notes

- Discovery starts from `https://bandi.regione.veneto.it/Public/Elenco`.
- The `Public/Index` page is registered as the portal entry point in `start_urls`.
- Candidate detail links are identified by path tokens: `dettaglio`, `bando`, `scheda`, `avviso`.
- Duplicate URLs are filtered during discovery using a `seen` set.
- **Pagination is not yet handled.** The URL pattern is unknown and must be validated
  with a live fixture before multi-page discovery is enabled.

## Fetch notes

- Each detail page HTML is fetched and stored as the primary evidence asset.
- PDF links found on the detail page are downloaded and stored as secondary assets.
- Fetch metadata (original URL, final URL, status code, body hash, timestamp) is
  preserved per `FetchRecord`.

## Extraction notes

- **Title**: extracted deterministically from `<h1>` or `<title>` using `HtmlExtractor`.
- **Publication date**: extracted by regex matching `Pubblicato il` or Italian date patterns.
- **Deadline**: extracted by regex matching `Scadenza` or `Termine` prefixes.
- **Authority**: attempted from `.ente-emittente` or related CSS class; falls back to
  regex extraction. The constant `Regione Veneto` can be applied at validation time.
- **Beneficiaries, eligible costs, summary, tags**: marked for optional AI enrichment.

## Known limitations

- Pagination is not implemented; only the first listing page is discovered.
- Detail URL heuristics (token matching) may miss records without those tokens in their path.
- The `authority` CSS selector is assumed; needs live validation.
- If the portal renders content via AJAX, GET-based discovery will be incomplete.
- POST-based search or session-gated content is not supported in the current adapter.

## Validation approach

Run `adapter-lab validate veneto_bandi` after a discovery + fetch cycle to check:

- Discovered detail URL count (expect > 0 per listing page)
- Fetched asset count per candidate
- PDF presence ratio (expect > 0.5 if PDFs are primary evidence)
- Missing title ratio (expect < 0.3 after fixture validation)
- Missing deadline ratio (acceptable to be high initially; improve regex before promotion)

## Test fixtures

Sample fixtures are in `tests/fixtures/veneto_bandi/`:

- `listing.html` — a representative listing page with detail anchors
- `detail.html` — a representative bando detail page with a PDF link

## Promotion-readiness notes

Before promoting to `STABLE`:

1. Validate discovery against live `/Public/Elenco` output.
2. Confirm detail URL token pattern with at least 10 real records.
3. Implement pagination once the URL pattern is confirmed.
4. Validate authority CSS selector against live detail pages.
5. Update fixtures from live snapshots and run regression tests.
6. Confirm deadline extraction accuracy against at least 5 records.
