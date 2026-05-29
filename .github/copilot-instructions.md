# Copilot Instructions for `pjbandi-adapter-lab`

## Repository purpose

This repository is a focused adapter lab for public funding and grant ingestion sources.

Its purpose is to:
- analyze official sources
- discover how sources expose opportunities
- prototype and refine ingestion adapters
- fetch and store raw evidence assets
- run deterministic extraction
- optionally enrich semantic fields with AI
- validate adapter quality
- build fixtures and regression checks
- prepare stable adapters for later promotion into another production repository

This repository is intentionally **not** the main product.

## What this repository must NOT become

Do NOT introduce or expand the repository toward:
- authentication
- authorization
- multi-tenancy
- billing
- user management
- customer-facing SaaS UI
- company-to-grant matching
- application workflows unrelated to adapter tuning
- complex orchestration not needed for adapter development

If a feature is more relevant to the production platform than to adapter tuning, do not implement it here.

## Primary architectural principles

### 1. Evidence-first ingestion
The repository treats source assets as first-class evidence.

Always preserve and work from raw evidence assets such as:
- HTML pages
- JSON responses
- PDF attachments
- DOC/DOCX/ZIP links (at minimum as metadata if not parsed)

Never skip raw evidence capture when implementing or modifying adapters.

### 2. Separate discovery, fetch, and extraction
Maintain strong separation of concerns:

- **discover()**
  - finds candidate detail pages or opportunity URLs

- **fetch()**
  - downloads and stores evidence assets

- **extract()**
  - interprets fetched assets and produces structured fields

Do not mix these steps into one monolithic function.

### 3. Deterministic first, AI second
Prefer deterministic extraction whenever possible.

Use deterministic methods for fields such as:
- title
- publication date
- deadline
- attachment links
- authority / issuer when clearly present

Use AI only for semantic enrichment where rules are insufficient, such as:
- beneficiaries
- eligible costs
- ineligible costs
- summary
- requirements interpretation
- thematic tagging

Do not rely on AI for critical structured metadata if a deterministic strategy is viable.

### 4. Source-specific adapters over generic scraping
Prefer clear source-specific or pattern-specific adapters over vague generic scrapers.

Good:
- source adapters extending a known pattern
- explicit logic for a known institutional source
- reusable pattern adapters with narrow responsibilities

Avoid:
- one-size-fits-all scraping abstractions
- overgeneralized crawler logic
- premature framework complexity

### 5. Small, explicit, testable design
Keep the codebase:
- small
- explicit
- type-safe
- readable
- testable
- easy to debug

Prefer explicit logic over clever abstraction.

## Repository coding standards

### General
- Use Python 3.12-compatible code
- Use type hints everywhere
- Add docstrings to public classes and functions
- Keep modules cohesive and small
- Prefer composition over deep inheritance unless inheritance is clearly helpful
- Avoid dead code and speculative abstractions
- Use logging for meaningful state transitions and failure points

### Models
Use typed models for core artifacts such as:
- SourceDefinition
- SourceProfile
- RawCandidate
- FetchRecord
- EvidenceAsset
- ExtractionResult
- ValidationReport

Models should be:
- explicit
- serializable
- easy to persist as JSON
- stable enough for fixtures and regression tests

### CLI
When changing CLI behavior:
- keep command names stable unless there is a strong reason
- keep help text clear
- ensure examples in README remain accurate
- verify new options have sensible defaults

Expected commands include:
- analyze
- discover
- fetch
- extract
- validate

### Storage
Prefer filesystem-based storage unless there is a compelling reason not to.

Use directories under `data/` consistently:
- `data/raw/`
- `data/extracted/`
- `data/profiles/`
- `data/fixtures/`
- `data/reports/`

Do not introduce a database unless it is clearly justified by a concrete repository need.

## Adapter implementation guidelines

### Discovery
Discovery logic should:
- start from one or more clear entry points
- identify likely detail pages
- support pagination when needed
- avoid uncontrolled crawling
- record useful metadata about discovered candidates

Prefer bounded and explainable discovery.

### Fetch
Fetch logic should:
- preserve original URL
- preserve final URL after redirects
- store timestamp
- store content type
- store status code
- store body hash
- save local file path
- create one or more EvidenceAsset records

If a source exposes PDF attachments, treat them as important evidence, not as optional extras.

### Extraction
Extraction should:
- consume fetched EvidenceAssets
- identify source-of-truth by field
- distinguish deterministic extraction from semantic enrichment
- record confidence or extraction origin if possible
- fail gracefully when evidence is partial

Do not silently invent missing fields.

### Validation
Validation should help answer:
- did discovery find enough plausible detail pages?
- did fetch capture the expected assets?
- are PDFs present where expected?
- how many records are missing title or deadline?
- is extraction minimally usable?

Validation output should be practical and readable.

## Testing rules

When creating or modifying functionality:
- add or update tests when reasonable
- prefer fixture-based tests over live network reliance
- keep integration-like tests credible but lightweight
- avoid brittle tests tied to unstable live pages unless explicitly marked

Regression safety matters more than broad test quantity.

## Documentation rules

Whenever you add or change behavior that affects users of the repository:
- update README if command usage changes
- update architecture/workflow docs if structure changes
- keep examples aligned with real code
- document assumptions when a source implementation is partial

Do not leave documentation stale after refactoring.

## AI enrichment rules

This repository may contain optional AI enrichment components, but they must remain:
- provider-agnostic
- optional
- replaceable
- clearly separated from deterministic extraction

Never hardwire a specific AI provider into the core architecture unless explicitly requested.

If AI behavior is stubbed or partial:
- make this obvious
- add TODO markers where useful
- keep interfaces clean

## Review and refactoring behavior

When asked to improve the repository:
1. preserve the repository mission
2. reduce complexity where possible
3. strengthen separation between discovery, fetch, extract, and validate
4. improve clarity before adding abstraction
5. verify imports and project structure consistency
6. verify CLI consistency
7. verify tests and docs still align with actual code

Prefer in-place refinement over unnecessary rewrites.

## Adding a new source

When adding support for a new source:
1. identify the source type
2. document assumptions
3. create or extend a suitable pattern adapter
4. implement source-specific logic explicitly
5. add sample fixtures if possible
6. validate the adapter with a realistic small sample
7. avoid coupling the new source to unrelated repository concerns

## What “done” means for an adapter

An adapter is considered in good shape when it can:
- discover plausible detail URLs
- fetch relevant evidence assets
- preserve raw evidence locally
- extract core deterministic fields
- produce a meaningful validation report
- be tested against sample fixtures
- remain understandable to a human reviewer

## Final instruction

When working in this repository, always optimize for:
- correctness
- transparency
- evidence preservation
- maintainability
- adapter quality
- low architectural noise

Do not optimize for product breadth.
Optimize for a clean and reliable adapter lab.
