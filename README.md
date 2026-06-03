# Adapter Lab

Adapter Lab is a focused Python repository for discovering, prototyping, and validating ingestion adapters for public funding and grant sources. It is designed as a practical lab: gather evidence from public websites, model a source, test extraction patterns, and decide whether an adapter is robust enough to promote into a production ingestion repository.

## What this repository is for

- analyzing unknown funding portals and bulletin sites
- capturing source profiles and evidence assets
- prototyping pattern adapters for recurring source shapes
- building source-specific adapters for Italian public funding sites
- validating extraction quality before promoting an adapter elsewhere
- preserving fixtures, reports, and extraction evidence for repeatable work

## What this repository intentionally does not do

This repository is not a SaaS product and does not try to be an end-user application. In particular it does **not**:

- provide user authentication or role management
- host a production ingestion platform
- perform applicant matching, eligibility scoring, or recommendation ranking
- manage submissions, workflows, or CRM-style pipelines
- provide a web UI or multi-tenant API
- replace source systems or production data warehouses

The goal is evidence-first adapter development, not a full platform.

## Architecture overview

The code is organized to keep reusable primitives separate from source logic:

- `src/adapter_lab/core/` – shared models, settings, storage, registry, pipeline orchestration
- `src/adapter_lab/cli/` – Typer commands for the lab workflow
- `src/adapter_lab/fetchers/` – HTTP fetching, asset download, content detection
- `src/adapter_lab/extractors/` – HTML, PDF, regex, and optional LLM enrichment helpers
- `src/adapter_lab/source_analysis/` – source profiling and adapter discovery support
- `src/adapter_lab/adapters/patterns/` – reusable adapter patterns for common source shapes
- `src/adapter_lab/adapters/sources/` – source-specific adapters registered in the runtime registry
- `src/adapter_lab/validation/` – checks, fixtures, regression helpers, and reports
- `data/` – local working evidence and generated artifacts
- `docs/` – architecture and workflow guidance

See `docs/architecture.md` for the full design rationale.

## CLI commands

The CLI is intentionally small and maps to the adapter lab lifecycle.

```bash
adapter-lab analyze https://bandi.regione.example.it
adapter-lab discover veneto_bandi --limit 20
adapter-lab fetch veneto_bandi --limit 10
adapter-lab extract veneto_bandi --limit 10
adapter-lab validate veneto_bandi
```

Equivalent module invocation:

```bash
python -m adapter_lab.main analyze https://www.incentivi.gov.it
python -m adapter_lab.main discover incentivi_gov
python -m adapter_lab.main fetch mimit --limit 5
python -m adapter_lab.main extract veneto_bandi --limit 5
python -m adapter_lab.main validate veneto_bandi
```

### Command behavior

- `analyze` inspects a starting URL, infers the likely source type, and writes a source profile under `data/profiles/`
- `discover` runs a registered adapter and stores discovered raw candidates
- `fetch` runs discovery, downloads candidate pages and linked assets, and stores raw evidence under `data/raw/`
- `extract` runs discovery and fetching as needed, then stores structured extraction results under `data/extracted/`
- `validate` runs the full adapter flow and writes validation reports under `data/reports/`

## Development setup

### Requirements

- Python 3.12
- pip

### Install

```bash
git clone https://github.com/aegidati/pjbandi-adapter-lab.git
cd pjbandi-adapter-lab
cp .env.example .env
pip install -e ".[dev]"
```

### Useful commands

```bash
make lint
make test
make test-unit
make test-integration
make extract SOURCE=veneto_bandi
make validate SOURCE=veneto_bandi
```

### TLS troubleshooting (corporate/self-signed certificates)

If commands such as `discover`, `fetch`, or `extract` fail with
`CERTIFICATE_VERIFY_FAILED`, configure one of these environment variables in `.env`:

- `HTTP_CA_BUNDLE`: path to your trusted corporate/root CA PEM bundle (recommended)
- `HTTP_VERIFY_SSL=false`: disable certificate verification only for local debugging

## How to add a new source

1. **Analyze the source**
   - Run `adapter-lab analyze <url>` on a representative listing page.
   - Review the generated profile in `data/profiles/`.
2. **Choose a pattern**
   - Match the source to `catalog_html`, `regional_html_pdf`, `pdf_first`, `api_backed`, or `legal_bulletin`.
3. **Create a source adapter**
   - Add a module under `src/adapter_lab/adapters/sources/`.
   - Inherit from the best matching pattern adapter.
   - Define `source_def` with stable identifiers and start URLs.
   - Override `discover`, `fetch`, or `extract` only where the source needs specialization.
4. **Register it**
   - Decorate the class with `@register_adapter("source_id")`.
   - Keep the module importable from `adapter_lab.adapters.sources/`; the CLI auto-loads source modules at startup.
5. **Capture fixtures**
   - Save stable HTML or JSON samples under `data/fixtures/<source_id>/` or `tests/fixtures/`.
6. **Validate behavior**
   - Run `discover`, `fetch`, `extract`, and `validate`.
   - Review reports and compare against expected fixtures.
7. **Mark readiness**
   - When confidence is high, update the source definition status from `draft` to `testing` or `stable`.

## How to promote an adapter to another repository

1. Confirm the adapter has stable discovery and extraction results.
2. Export or document the source profile, fixtures, and validation reports.
3. Move the relevant source adapter plus any specialized parsing helpers into the target ingestion repository.
4. Re-map storage and orchestration hooks to the production repository conventions.
5. Re-run fixture-based and target-repository tests there.
6. Keep the lab copy as a reference until the production adapter is proven in the destination repository.

Promotion should be deliberate: this repo is where patterns are explored and hardened before they become production code.

## Data directories

- `data/raw/` – fetched source pages and binary assets
- `data/extracted/` – structured extraction output
- `data/profiles/` – inferred source profiles from analysis
- `data/fixtures/` – committed regression fixtures
- `data/reports/` – validation reports and summaries

## Repository mindset

The lab follows an evidence-first workflow: fetch the actual public artifact, preserve it locally, extract deterministically first, and treat LLM enrichment as optional. That keeps adapter work inspectable, repeatable, and easy to promote.
