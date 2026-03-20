# Testing Patterns

**Analysis Date:** 2026-03-20

## Test Framework

**Runner:**
- None — no test framework configured

**Assertion Library:**
- None

**Run Commands:**
```bash
# No automated test commands available
# Manual verification per README.md:
# Review output/raw_candidates.csv and output/fetch_log.csv after each run
```

## Test File Organization

**Location:**
- No test files exist
- No `tests/` directory
- No `test_*.py` or `*_test.py` files
- No `conftest.py`

**Naming:**
- Not applicable

## Test Structure

**No automated tests.** The project uses manual verification as its quality gate:

1. Run `collect.py` to produce `output/raw_candidates.csv`
2. Operator reviews candidates for name, title, profile URL, email accuracy
3. Operator checks `output/fetch_log.csv` for fetch errors and coverage gaps
4. Verified candidates published to Google Sheets

## Testing Approach

**Manual/Integration Testing:**
- Designed for human review as documented in `README.md`
- `fetch_log.csv` provides structured run diagnostics (institution, url, status, detail)
- Status values: `"ok"`, `"skipped"`, `"http_error"`, `"url_error"`, `"error"`
- Checkpoint saves (`--save-every`) allow reviewing partial results mid-run

**Coverage Awareness:**
- Single `# pragma: no cover` annotation in `src/gis_librarians/collect.py:492`
- Indicates awareness of coverage tooling but not actively configured

## Mocking

**Not applicable** — no test suite.

If tests are added, key areas to mock:
- `urllib.request.urlopen` — all HTTP calls
- CSV file I/O — to avoid filesystem side effects
- `time.sleep` — to speed up tests

## Coverage

**Requirements:**
- No coverage targets or enforcement

**Configuration:**
- No coverage tool configured

## Test Types

**Unit Tests:**
- Not present
- High-value candidates for unit testing:
  - `score_ror_item()` in `enrich_r1_institutions.py` (complex scoring logic)
  - `is_plausible_candidate()` in `collect.py` (boolean filter with multiple conditions)
  - `normalize_name()`, `compress_name()` (string transformation functions)
  - `extract_candidates()` in `collect.py` (HTML → structured data)

**Integration Tests:**
- Not present
- Would require mocking external HTTP calls (ROR API, institution websites)

**E2E Tests:**
- Not present — manual run against live sites serves as de-facto E2E

## Adding Tests

If adding a test suite, recommended approach:
1. Add `pytest` to a `requirements-dev.txt`
2. Create `tests/` directory alongside `src/`
3. Use `pytest` with `unittest.mock.patch` for `urllib.request.urlopen`
4. Start with pure functions: scoring, normalization, plausibility checks
5. Add fixture HTML files in `tests/fixtures/` for HTML parsing tests

---

*Testing analysis: 2026-03-20*
*Update when test patterns change*
