# Copilot instructions for this repository

- Keep changes evidence-first: preserve the staged flow of analyze -> discover -> fetch -> extract -> validate.
- Prefer refining pattern adapters and thin source adapters over adding source-specific duplication.
- Add new source adapters under `src/adapter_lab/adapters/sources/` and register them with `@register_adapter`.
- Do not hardcode new source imports in the CLI entrypoint; rely on package-level source auto-loading.
- Keep CLI examples and Makefile targets aligned with `python -m adapter_lab.main` and the `adapter-lab` entrypoint.
- When updating extraction behavior, keep tests in `tests/unit/` and `tests/integration/` consistent with the persisted raw/extracted/report artifacts.
- Prefer minimal, inspectable changes over framework-heavy abstractions or hidden magic.
