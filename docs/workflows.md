# Workflows

## End-to-end pipeline

Adapter Lab supports a full workflow from source discovery to validation.

### 1. Analyze

Goal: inspect an unknown source and infer which adapter pattern is likely to fit.

```bash
adapter-lab analyze https://www.incentivi.gov.it
```

Outputs:

- inferred `SourceType`
- candidate link sample
- pagination hints
- attachment hints
- saved source profile in `data/profiles/`

### 2. Discover

Goal: produce raw candidate URLs for a known source adapter.

```bash
adapter-lab discover incentivi_gov --limit 20
```

Outputs:

- `RawCandidate` objects
- saved NDJSON snapshots for repeatable inspection

### 3. Fetch

Goal: download candidate pages and linked evidence assets.

```bash
adapter-lab fetch mimit --limit 10
```

Outputs:

- `FetchRecord` objects
- saved HTML, PDF, or JSON evidence in `data/raw/`
- derived `EvidenceAsset` records

### 4. Extract

Goal: turn evidence into structured fields.

```bash
adapter-lab extract veneto_bandi --limit 10
```

Outputs:

- titles
- publication dates
- deadlines
- attachment URLs
- raw and semantic fields
- extraction notes for incomplete cases

### 5. Validate

Goal: measure whether the adapter is ready for wider use.

```bash
adapter-lab validate veneto_bandi
```

Outputs:

- candidate count checks
- fetch coverage
- PDF presence ratio
- title and deadline completeness
- extraction completeness score
- JSON reports in `data/reports/`

## Practical workflow for a new source

1. Run `analyze` on the suspected listing page.
2. Select the closest pattern adapter.
3. Implement a source adapter under `adapters/sources/`.
4. Save at least one stable fixture.
5. Run `discover`, `fetch`, and `extract` against the adapter.
6. Run `validate` and inspect the report.
7. Iterate until the extraction is stable enough to promote.

## Failure handling

- If discovery fails, inspect the saved listing HTML or the fixture sample.
- If fetch coverage is low, review redirect handling and attachment detection.
- If extraction completeness is poor, inspect deterministic patterns before adding any AI enrichment.
- If validation regresses, compare current output to stored fixtures.

## Why the workflow is split

The split pipeline is intentional. Public funding sources change often, so separating discovery, fetch, extraction, and validation makes debugging faster and keeps evidence available for later review.
