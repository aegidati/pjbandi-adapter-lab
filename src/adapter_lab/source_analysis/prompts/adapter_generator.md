# Adapter Generator Prompt Template

Use this prompt to draft a source-specific adapter after a profile is available.

## Inputs

- source profile JSON
- representative HTML/PDF/JSON fixtures
- target pattern adapter

## Expected output

- `source_def` proposal
- overridden methods required for discovery or extraction
- selectors and assumptions justified by the fixture evidence
- open questions that must be validated with fixtures or manual review
