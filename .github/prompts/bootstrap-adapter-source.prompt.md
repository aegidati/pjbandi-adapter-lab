---
name: bootstrap-adapter-source
description: Analyze a new public funding source and scaffold or refine a source adapter, source profile, fixtures, and validation artifacts.
argument-hint: "<start-url> <source-id> [optional notes]"
agent: agent
---

# Mission

You are working inside the `pjbandi-adapter-lab` repository.

Your task is to bootstrap support for a **new funding source** starting from a user-provided URL and a desired source ID.

You must follow the repository rules defined in:
- `.github/copilot-instructions.md`

This repository is an **adapter lab**, not the final product.

Do NOT introduce:
- authentication
- authorization
- multi-tenancy
- billing
- user management
- product UI features
- company-to-grant matching
- unrelated SaaS concerns

Focus only on:
- source analysis
- source profiling
- adapter scaffolding or refinement
- evidence-first ingestion
- deterministic extraction
- optional AI enrichment hooks
- validation
- fixtures
- documentation

---

# User input

Interpret the user arguments as:

1. `start_url`
   - the initial URL to inspect

2. `source_id`
   - a short snake_case identifier for the source
   - examples: `veneto_bandi`, `mimit`, `incentivi_gov`

3. `notes`
   - optional free-form notes from the user
   - use them as hints, not as guaranteed truth

If some input is missing, ask only for the minimum necessary clarification.

---

# Objectives

Bootstrap support for the source by doing the following:

## 1. Inspect repository context
- Read `.github/copilot-instructions.md`
- Inspect the current repository structure
- Reuse existing patterns before creating new abstractions
- Prefer extending or specializing an existing pattern adapter if appropriate

## 2. Analyze the source
Starting from `start_url`, determine as much as possible about the source:

- source type:
  - catalog
  - institutional listing
  - regional portal
  - pdf-first source
  - api-backed source
  - legal bulletin source
  - mixed

- likely navigation model:
  - listing page
  - detail page
  - attachment/document
  - pagination
  - filters/search forms
  - API/XHR hints if visible

- likely source-of-truth by field:
  - HTML
  - PDF
  - JSON
  - legal act
  - mixed

- likely risks:
  - listing only / teaser pages
  - JS-rendered content
  - hidden pagination
  - attachment-only detail
  - redirects
  - duplicate records
  - rectifications / extensions

## 3. Create or update a Source Profile
Create or update a profile file under:

- `data/profiles/<source_id>.source-profile.json`

The profile should include at least:
- source_id
- entry_url
- source_type
- discovery strategy
- fetch strategy
- extraction hints
- evidence priority
- known risks
- assumptions
- open questions

If live inspection is incomplete, still create the profile with explicit assumptions.

## 4. Scaffold or refine the source adapter
Create or update a source adapter under:

- `src/adapter_lab/adapters/sources/<source_id>.py`

Rules:
- Keep the adapter explicit and source-focused
- Reuse a suitable pattern adapter when possible
- Maintain separation between:
  - `discover()`
  - `fetch()`
  - `extract()`
- Do not mix network fetching and semantic interpretation in one monolithic block
- Preserve evidence-first behavior

If the correct pattern is unclear, choose the simplest plausible pattern and document the assumption.

## 5. Add or update source documentation
Create or update:

- `docs/sources/<source_id>.md`

This document should include:
- source name
- start URL
- source type
- adapter strategy
- discovery notes
- fetch notes
- extraction notes
- known limitations
- validation approach
- promotion-readiness notes

## 6. Add fixtures and tests
Add minimal but credible artifacts for regression and validation.

Use or create folders such as:
- `tests/fixtures/<source_id>/`
- `data/fixtures/<source_id>/` if appropriate

Then add or update tests so the source has at least:
- a minimal adapter loading/import test
- a fixture-based test if feasible
- a validation-oriented smoke test if feasible

Prefer lightweight, deterministic tests over brittle live-network tests.

## 7. Add validation support
Ensure the source can participate in validation workflows.

If needed, update or extend validation logic so this source can be checked for:
- discovered detail count
- fetched asset count
- pdf presence
- missing title ratio
- missing deadline ratio
- extraction completeness

## 8. Keep the repository coherent
When making changes:
- verify imports
- verify module paths
- verify CLI consistency if new registration is needed
- verify docs match implementation
- keep the codebase small and readable

---

# Implementation preferences

## Prefer deterministic first
Use deterministic extraction for fields such as:
- title
- publication date
- deadline
- attachment links

Use AI only as optional semantic enrichment for:
- beneficiaries
- eligible costs
- requirements
- summary
- tags

## Prefer source-specific clarity
Do not build an overgeneric crawler.
Prefer:
- explicit source logic
- explicit assumptions
- explicit evidence handling

## Preserve raw evidence thinking
Even if the adapter is only scaffolded, structure it as if evidence assets matter:
- HTML
- JSON
- PDF
- attachments metadata

---

# Constraints

## If network access or source inspection is limited
If you cannot fully inspect the source:
- still generate the source profile
- still scaffold the adapter
- mark assumptions clearly
- leave focused TODOs only where unavoidable
- avoid leaving the source unsupported just because inspection is partial

## Avoid noise
Do not introduce:
- unrelated files
- speculative frameworks
- unused abstractions
- product-level features

---

# Expected outputs

You should produce **real repository changes**, not just suggestions.

At minimum, aim to create or update:

- `data/profiles/<source_id>.source-profile.json`
- `src/adapter_lab/adapters/sources/<source_id>.py`
- `docs/sources/<source_id>.md`

And, if feasible:
- source registration updates
- fixture files
- tests
- validation/report support

---

# Final response format

At the end of the task, provide a concise summary with:

1. What source type you identified
2. Which files were created or updated
3. Which assumptions were made
4. What remains manual or uncertain
5. What the next best validation step is

Be concrete.
Prefer implementation over theory.
Keep the repository aligned with its adapter-lab mission.
