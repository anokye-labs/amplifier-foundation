# Amplifier Foundation

Foundational Python library for the Amplifier ecosystem: bundle composition, @mention resolution, utilities, and reference content.

## Tech Stack
- Python 3.11+
- Build: uv / pip
- Testing: pytest
- No framework — pure Python library

## Build & Test
```bash
# Install with uv
uv pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v
```

## Project Structure
- `amplifier_foundation/` — Core library package
  - `bundle.py` — Bundle loading, composition, validation
  - `mentions/` — @mention parsing and resolution (`@namespace:path`)
  - `discovery/` — Module and bundle discovery
  - `io/` — YAML/frontmatter I/O, file utilities
  - `cache/` — Caching utilities
  - `dicts/` — Dict merging utilities
  - `paths/` — Path handling
  - `session/` — Session management
  - `sources/` — Bundle source loaders (local, remote)
  - `registry.py` — Module registry
  - `validator.py` — Bundle validation
- `tests/` — Test suite
- `bundles/` — Reference bundle definitions
- `modules/` — Reference modules
- `providers/` — Reference provider configurations
- `agents/` — Reference agent definitions
- `behaviors/` — Reference behavior definitions
- `recipes/` — Reference recipes
- `scripts/` — Maintenance and analysis scripts

## Conventions
- Ultra-thin mechanism layer — provides mechanisms, not policies
- Bundle system is the primary abstraction for composing agent configurations
- `@namespace:path` mentions resolve references across bundles
- YAML frontmatter is the standard metadata format

## Important Notes
- This library is consumed by amplifier-core and other Amplifier components
- Reference content in `bundles/`, `agents/`, `behaviors/` etc. serves as examples and defaults
