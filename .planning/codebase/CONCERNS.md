# Codebase Concerns

**Analysis Date:** 2026-03-20

## Tech Debt

**Duplicated utility functions:**
- Issue: `write_csv()` defined identically in `fetch_r1_institutions.py`, `fetch_arl_members.py`, and `enrich_r1_institutions.py`; `normalize_space()` duplicated in `collect.py` and `fetch_arl_members.py`
- Why: Each module written independently without shared utilities
- Impact: Bug fixes or changes must be applied in multiple places
- Fix approach: Extract to `src/gis_librarians/utils.py`

**Hardcoded output paths in fetch scripts:**
- Issue: `RAW_OUTPUT` and `TEMPLATE_OUTPUT` are hardcoded constants in `fetch_r1_institutions.py:14-15`; same in `fetch_arl_members.py:16-17`; `ALIASES_PATH` and `ARL_PATH` in `enrich_r1_institutions.py:41-42` not configurable via CLI
- Why: Simple scripts written for single-use
- Impact: Cannot run from different working directories; hard to integrate into pipelines
- Fix approach: Promote to `argparse` arguments with sensible defaults

## Known Bugs / Documented Limitations

**Multi-person directory page parsing fails:**
- Symptoms: Mixed staff entries in a single paragraph block produce garbled or merged candidates
- Trigger: Library pages where multiple people appear in dense paragraphs (not structured lists/tables)
- Files: `src/gis_librarians/collect.py:333` — sentence splitting on `.!?` is insufficient
- Documented in: `docs/CONTEXT.md:54`, `STATUS.md:33`
- Workaround: Manual review filters bad extractions
- Root cause: No per-person segmentation logic; extractor treats block as single candidate context

## Security Considerations

**Placeholder contact URL in User-Agent:**
- Risk: Default User-Agent in `collect.py:411` contains `https://example.org/contact`, a non-real URL
- Current mitigation: Configurable via `--user-agent`
- Recommendation: Update to real project URL or remove example.org reference

**No pre-flight URL validation:**
- Risk: Malformed URLs from CSV data passed directly to `urllib.request.urlopen` without validation
- Files: `enrich_r1_institutions.py:108-118` (`fetch_json`, `fetch_html`), `collect.py:183-189` (`fetch_url`)
- Current mitigation: `urllib.error.URLError` caught and logged
- Recommendation: Add basic URL scheme validation before requests

## Performance Bottlenecks

**Rate limiting is per-institution, not per-request:**
- Problem: `--delay` applies once per row/institution, but multiple HTTP calls are made per institution (ROR query + homepage crawl in enrichment; common path probes + discovered links in collection)
- Files: `enrich_r1_institutions.py:466`, `collect.py:501`
- Cause: Inner-loop fetches not individually delayed
- Impact: External APIs and institution sites may throttle (documented: 429 responses logged in `docs/CONTEXT.md:61`)
- Improvement path: Add per-request delay inside `fetch_url()` and `fetch_json()`/`fetch_html()`

**No retry logic for rate-limited responses:**
- Problem: HTTP 429 and 401 responses logged and skipped — no retry or backoff
- File: `src/gis_librarians/collect.py:474-482`
- Documented in: `docs/CONTEXT.md:61`
- Impact: Institutions with protected or rate-limited staff pages are silently under-collected
- Improvement path: Add exponential backoff with configurable retry count

## Fragile Areas

**Broad exception handling in enrichment:**
- Files: `src/gis_librarians/enrich_r1_institutions.py:314` (`url_reachable()`), `:328-329` (`discover_library_url()`), `:338-339` (`discover_directory_url()`)
- Why fragile: `except Exception: pass` silently swallows timeouts, DNS failures, malformed responses — indistinguishable from expected misses
- Safe modification: Replace with specific exceptions (`HTTPError`, `URLError`, `socket.timeout`) and log failures
- Test coverage: None

## Missing Critical Features

**No retry/backoff for rate-limited responses:**
- Problem: 429 and 401 responses silently drop institutions from collection
- Current workaround: Manual re-runs with `--only-missing`
- Blocks: Complete coverage of large institution lists
- Implementation complexity: Low (add retry loop with sleep in `fetch_url()`)

**No test suite:**
- Problem: Complex scoring and extraction logic has no automated verification
- Current workaround: Manual review of `raw_candidates.csv`
- Risk: Regressions in scoring functions, keyword lists, or HTML parsing go undetected
- High-value targets: `score_ror_item()`, `is_plausible_candidate()`, `extract_candidates()`, normalization helpers

## Test Coverage Gaps

**Scoring functions:**
- What's not tested: `score_ror_item()` weighting, threshold behavior, edge cases
- Risk: Threshold changes (currently magic numbers) could silently change match quality
- Priority: High
- Files: `src/gis_librarians/enrich_r1_institutions.py:145-177`

**HTML extraction logic:**
- What's not tested: `extract_candidates()`, `LinkTextParser`, `is_plausible_candidate()`
- Risk: HTML structure changes in library websites break extraction silently
- Priority: High
- Files: `src/gis_librarians/collect.py:125-164`, `collect.py:333-420`

**Normalization helpers:**
- What's not tested: `normalize_name()`, `compress_name()`, `normalize_space()`
- Risk: Edge cases (Unicode, punctuation, empty strings) not covered
- Priority: Medium
- Files: `src/gis_librarians/enrich_r1_institutions.py`, `src/gis_librarians/collect.py`

## Dependencies at Risk

**No external dependencies** — stdlib only. No dependency risk.

---

*Concerns audit: 2026-03-20*
*Update as issues are fixed or new ones discovered*
