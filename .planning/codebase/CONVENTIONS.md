# Coding Conventions

**Analysis Date:** 2026-03-20

## Naming Patterns

**Files:**
- snake_case for all Python modules: `fetch_r1_institutions.py`, `enrich_r1_institutions.py`, `collect.py`
- Verb-first action naming for pipeline scripts

**Functions:**
- snake_case for all functions: `fetch_url()`, `extract_candidates()`, `discover_urls()`, `score_ror_item()`
- Descriptive verb+noun form
- No special prefix for async (not used) or private (no convention)

**Variables:**
- snake_case for variables and parameters
- UPPER_SNAKE_CASE for module-level constants: `KEYWORDS`, `COMMON_PATHS`, `EMAIL_RE`, `ROR_API_URL`
- Regex constants suffixed with `_RE`: `EMAIL_RE`, `WHITESPACE_RE`, `NAME_RE`

**Classes:**
- PascalCase: `LinkTextParser`, `ParagraphLinkParser`, `LinkParser`, `Candidate`
- HTMLParser subclasses named after their extraction role

## Code Style

**Formatting:**
- No formatter configured (no .black, ruff.toml, or .prettierrc)
- 4-space indentation consistently applied
- Double quotes (100%) for all string literals
- Triple double quotes for docstrings: `"""..."""`
- Line length: ~120 characters (varies by file, no enforced max)

**Linting:**
- No linting configuration detected
- Consistent style maintained manually

**Shebang:**
- All scripts: `#!/usr/bin/env python3`
- All files: `from __future__ import annotations` (first import)

## Import Organization

**Order:**
1. `from __future__ import annotations`
2. Standard library imports (alphabetical within group)
3. Module-level constants and compiled regexes
4. Class definitions
5. Function definitions
6. `main()` and `if __name__ == "__main__"` block

**Grouping:**
- Blank line between stdlib imports and constants
- No path aliases (flat stdlib imports)

## Error Handling

**Patterns:**
- Specific exception types preferred: `HTTPError`, `URLError` caught separately in `collect.py`
- Try-except wraps individual HTTP calls, not entire functions
- Failures logged to CSV (`fetch_log.csv`) then execution continues

**Error Types:**
- `urllib.error.HTTPError` — for HTTP status errors (4xx, 5xx)
- `urllib.error.URLError` — for network/connection errors
- Broad `except Exception` used in `enrich_r1_institutions.py` (flagged in CONCERNS.md)

**Logging:**
- No logging framework — print() for progress, CSV for structured failure records
- `fetch_log.csv` records: institution, url, status, detail

## Type Hints

**Coverage:**
- Comprehensive type hints on all function signatures
- Parameters, return types, and complex variables annotated

**Style:**
- Modern Python 3.10+ syntax: `str | None` (not `Optional[str]`)
- Built-in generics: `list[str]`, `dict[str, str]` (not `List`, `Dict` from typing)
- `from __future__ import annotations` enables forward references

**Examples from `src/gis_librarians/collect.py`:**
```python
def fetch_url(url: str, user_agent: str, timeout: int) -> tuple[str, str]:
def extract_candidates(...) -> list[Candidate]:
def is_plausible_candidate(source_url: str, sentence: str, ...) -> bool:
```

## Script Structure

All 4 pipeline scripts follow this pattern:

```python
#!/usr/bin/env python3
"""Module docstring."""
from __future__ import annotations

# stdlib imports
import argparse
import csv
...

# Module-level constants
CONSTANT = "value"
REGEX = re.compile(r"pattern")

# Class definitions
class SomeParser(HTMLParser): ...

# Function definitions
def helper_function() -> ...: ...

def main() -> int:
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()
    ...
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Comments

**When to Comment:**
- Module docstrings on all files (all 4 present)
- Class docstrings on HTMLParser subclasses (present in `collect.py`)
- No function-level docstrings (absent throughout)
- Inline comments minimal — code is self-documenting via naming

**Special Annotations:**
- `# pragma: no cover` used for unreachable exception handlers in `collect.py:492`

## Data Patterns

**CSV I/O:**
- Standard `csv.DictReader` / `csv.DictWriter`
- Rows processed as dicts; fieldnames from schema
- In-place CSV update pattern (read all → update → write all) in `enrich_r1_institutions.py`

**Dataclasses:**
- `@dataclass` for structured output: `Candidate` in `collect.py`
- Flat field names (no nesting)

---

*Convention analysis: 2026-03-20*
*Update when patterns change*
