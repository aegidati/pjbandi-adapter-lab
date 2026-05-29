# Architecture

## Core concepts

Adapter Lab is built around a simple but strict data flow:

1. **Analyze a source** to understand its structure and likely pattern.
2. **Discover candidates** such as grant detail pages, PDFs, or API items.
3. **Fetch evidence** and persist the raw artifacts.
4. **Extract structured fields** from HTML, PDFs, or JSON.
5. **Validate quality** with repeatable checks and fixtures.

Every stage is explicit and serializable. This makes it easy to inspect failures, compare runs, and promote only the adapters that are trustworthy.

## Evidence-first approach

The repository treats fetched artifacts as evidence, not transient implementation details.

- raw pages and files are stored under `data/raw/`
- extracted records are stored under `data/extracted/`
- source profiles are stored under `data/profiles/`
- validation output is stored under `data/reports/`
- fixtures live under `data/fixtures/` and `tests/fixtures/`

This evidence-first approach supports repeatable debugging. If an extraction fails, the team can inspect the saved HTML or PDF instead of guessing what changed upstream.

## Module responsibilities

### `adapter_lab.core`

- `types.py` defines shared enums and aliases
- `models.py` defines pydantic data contracts for sources, candidates, fetches, assets, extractions, and reports
- `settings.py` loads environment-based configuration
- `storage.py` handles JSON, NDJSON, and binary persistence
- `registry.py` maps source IDs to adapter classes
- `pipeline.py` orchestrates end-to-end execution

### `adapter_lab.fetchers`

- `http_fetcher.py` performs HTTP retrieval with retry logic and persistence
- `content_detector.py` classifies fetched content
- `download_manager.py` turns URLs into evidence assets
- `browser_fetcher.py` is a deliberate stub for future JS-rendered sources

### `adapter_lab.extractors`

- `html_extractors.py` parses HTML titles, links, and text
- `pdf_extractors.py` extracts text from PDF bytes or files
- `regex_extractors.py` provides deterministic funding-oriented extraction logic
- `llm_enrichment.py` provides a pluggable enrichment abstraction

### `adapter_lab.source_analysis`

This package helps determine what kind of adapter should be built. It performs a lightweight inspection without requiring an LLM.

### `adapter_lab.adapters`

Pattern adapters encode common discovery and extraction strategies. Source adapters inherit from them and contain only the selectors or logic unique to a given source.

### `adapter_lab.validation`

Validation components measure completeness and coverage, compare current output to fixtures, and write human- and machine-readable reports.

## Pattern adapters vs source adapters

Pattern adapters are the reusable center of the design.

- **Pattern adapters** solve recurring structures such as listing pages with detail pages, HTML plus PDF detail flows, PDF-first bulletin repositories, or JSON APIs.
- **Source adapters** are thin layers that define source metadata and override only the discovery or extraction pieces that differ.

This separation avoids copying extraction logic into every source implementation.

## Data flow in practice

A typical run looks like this:

- `Pipeline.run_discover(source_id)` loads a registered source adapter
- the adapter produces `RawCandidate` objects
- `Pipeline.run_fetch(source_id)` fetches candidates and stores `FetchRecord` and `EvidenceAsset` records
- `Pipeline.run_extract(source_id)` extracts structured `ExtractionResult` records
- `Pipeline.run_validate(source_id)` computes a `ValidationReport`

Each stage can be rerun independently. This is useful when a selector changes but the raw evidence is already available.

## AI enrichment pluggability

LLM use is optional by design.

- deterministic parsing remains the default and the primary path
- the `LlmEnricher` abstraction can enrich extracted text with semantic fields later
- the initial implementation returns an empty enrichment payload and logs a warning
- prompt templates live under `source_analysis/prompts/` for future iterative work

This keeps the repository operational without vendor lock-in while preserving a clear integration point for AI-assisted enrichment or adapter generation.
