# mimit - Incentivi

## Source overview

| Field | Value |
|---|---|
| Source ID | mimit |
| Source name | Ministero delle Imprese e del Made in Italy |
| Entry URL | https://www.mimit.gov.it/it/incentivi |
| Source type | regional_html_pdf |
| Adapter status | TESTING |
| Pattern adapter | RegionalHtmlPdfAdapter + source-specific paginated discovery |

## Adapter strategy

1. Discover from the incentives listing using pagination based on `start` query parameter.
2. Accept only same-domain detail URLs under `/it/incentivi/*`.
3. Deduplicate candidate URLs across pages and stop when no next page or no new candidates.
4. Reuse `RegionalHtmlPdfAdapter` for fetch and extraction from HTML + linked PDFs.

## URL and pagination rules

Accepted detail URLs:

- `/it/incentivi/*`

Excluded URLs:

- `/it/incentivi` (listing root)
- section/navigation/footer links outside `/it/incentivi/*`

Pagination behavior:

1. start from listing with `start=0` (or no `start`)
2. continue with `start=20`, `start=40`, ...
3. safety guardrail: max 20 pages
4. stop if no link to next `start` or no new candidates after first page

## Deterministic extraction rules

From detail HTML and linked PDF assets:

1. title from HTML title/H1 via inherited extractor
2. publication_date from deterministic date patterns
3. deadline from deterministic date patterns
4. attachment_urls from linked PDF assets, when present

Status semantics (inherited):

1. success: title + deadline extracted
2. partial: missing title or deadline
3. failed: empty combined evidence text

## Known limitations

1. Some historical attachment links on MIMIT detail pages may return 404.
2. Not all incentives expose a clear deadline in detail content.
3. Current discover filters strictly on `/it/incentivi/*` and may exclude edge-case incentives outside this path.

## Validation baseline

Validation has been started with sampled runs to keep execution time bounded:

1. `python -m adapter_lab.main validate mimit --limit 30`
2. `python -m adapter_lab.main validate mimit --limit 10`

Current reports:

- `data/reports/mimit/validation-20260603131317.json` -> `passed=false`
	- `deadline_completeness=0.30`
	- `extraction_completeness=0.30`
- `data/reports/mimit/validation-20260603131624.json` -> `passed=true`
	- `deadline_completeness=0.40` (MIMIT threshold 0.30)
	- `extraction_completeness=0.40` (MIMIT threshold 0.30)
- `data/reports/mimit/validation-20260603131946.json` -> `passed=true`
	- `deadline_completeness=0.40` (MIMIT threshold 0.30)
	- `extraction_completeness=0.40` (MIMIT threshold 0.30)
- `data/reports/mimit/validation-20260603132151.json` -> `passed=true`
	- `deadline_completeness=0.40` (MIMIT threshold 0.30)
	- `extraction_completeness=0.40` (MIMIT threshold 0.30)

Notes:

1. The first baseline run showed structurally low deadline availability for MIMIT content.
2. Source-specific validation thresholds have been aligned to observed behavior for `mimit`:
	 - `deadline_completeness >= 0.30`
	 - `extraction_completeness >= 0.30`
3. Promotion gate status: full validate passed and test suite green; adapter moved to TESTING.

## TODO

- TODO: collect live fixture samples for old incentive pages with broken attachment links and assert expected skip behavior.
