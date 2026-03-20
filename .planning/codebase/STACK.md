# Technology Stack

**Analysis Date:** 2026-03-20

## Languages

**Primary:**
- Python 3.10+ - All application code (`src/gis_librarians/*.py`)
  - Uses `from __future__ import annotations` for forward references
  - Modern union syntax (`|`), `list[]`/`dict[]` built-in generics

**Secondary:**
- None

## Runtime

**Environment:**
- Python 3.10+ (required for modern type hint syntax)
- No virtual environment or lockfile — stdlib only, no external packages

**Package Manager:**
- None required — zero external dependencies
- No `requirements.txt`, `pyproject.toml`, `setup.py`, or `Pipfile`

## Frameworks

**Core:**
- None (pure Python CLI scripts)

**Testing:**
- None (no test framework configured)

**Build/Dev:**
- None (direct script execution via `python src/gis_librarians/<script>.py`)

## Key Dependencies

**Critical (stdlib only):**
- `urllib.request`, `urllib.parse`, `urllib.error` — HTTP client for all web fetching
- `html.parser.HTMLParser` — HTML parsing (custom subclasses per module)
- `csv` — All CSV I/O (reading input templates, writing output)
- `json` — Parsing ROR API responses
- `argparse` — CLI argument handling in all scripts
- `dataclasses` — `Candidate` structured data type in `collect.py`
- `re` — Email and name extraction regexes
- `pathlib` — File path handling

## Configuration

**Environment:**
- No environment variables used
- No `.env` or config files
- All settings passed via CLI arguments at runtime

**Build:**
- No build configuration files

## Platform Requirements

**Development:**
- Any platform with Python 3.10+
- No external services required for local use

**Production:**
- Runs locally or on any Unix machine with Python 3.10+
- Not deployed — operator-run pipeline scripts

---

*Stack analysis: 2026-03-20*
*Update after major dependency changes*
