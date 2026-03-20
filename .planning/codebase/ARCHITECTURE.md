# Architecture

**Analysis Date:** 2026-03-20

## Pattern Overview

**Overall:** Sequential ETL Pipeline (4-stage data collection and enrichment)

**Key Characteristics:**
- Each stage is an independent, resumable CLI script
- Data flows between stages via CSV files on disk
- Checkpoint saves every N records for safe interruption/resumption
- Conservative, keyword-centric extraction reduces false positives
- No shared state between stages — file-based handoff only

## Layers

**Fetching Layer:**
- Purpose: Download raw data from authoritative external sources
- Contains: `fetch_r1_institutions.py`, `fetch_arl_members.py`
- Depends on: Carnegie Classifications API, ARL website
- Used by: Feeds `data/raw/` and `data/reference/` for enrichment

**Enrichment Layer:**
- Purpose: Augment raw institution list with website and library URLs
- Contains: `enrich_r1_institutions.py`
- Depends on: ROR API, institution homepages, `data/reference/arl_members.csv`, `data/reference/institution_aliases.csv`
- Used by: Produces enriched `data/r1_institutions_template.csv` for collection

**Collection Layer:**
- Purpose: Crawl library staff/directory pages and extract GIS librarian candidates
- Contains: `collect.py`
- Depends on: Enriched institution CSV, institution library websites
- Used by: Produces `output/raw_candidates.csv` for manual review

**Utility/Support:**
- Custom `HTMLParser` subclasses in each module
- Scoring algorithms for fuzzy name matching (ROR, ARL)
- CSV I/O helpers (duplicated across modules — see CONCERNS.md)

## Data Flow

**Pipeline Execution:**

1. Run `fetch_r1_institutions.py` → downloads Carnegie R1 list → writes `data/raw/carnegie_r1_2025.csv` + `data/r1_institutions_template.csv`
2. Run `fetch_arl_members.py` → scrapes ARL website → writes `data/reference/arl_members.csv`
3. Run `enrich_r1_institutions.py` → queries ROR API + crawls homepages → enriches `data/r1_institutions_template.csv` in-place
4. Run `collect.py` → crawls library staff/guide pages → writes `output/raw_candidates.csv` + `output/fetch_log.csv`
5. Manual review and Google Sheets publication

**State Management:**
- File-based: all state lives in `data/` and `output/` directories
- Checkpoint saves every N records (configurable `--save-every`)
- `--only-missing` flag on enrichment skips already-processed rows

## Key Abstractions

**HTMLParser Subclasses:**
- Purpose: Extract structured data (text, links) from raw HTML
- Examples: `LinkTextParser` (`collect.py`), `ParagraphLinkParser` (`fetch_arl_members.py`), `LinkParser` (`enrich_r1_institutions.py`)
- Pattern: Override `handle_starttag`, `handle_endtag`, `handle_data` methods

**Candidate Dataclass:**
- Purpose: Structured container for extracted GIS librarian records
- Location: `src/gis_librarians/collect.py`
- Fields: institution, source_url, keyword, excerpt, name, title, email, profile_url

**Scoring Functions:**
- Purpose: Fuzzy matching of institution names across data sources
- Examples: `score_ror_item()`, `score_arl_match()` in `enrich_r1_institutions.py`
- Pattern: Weighted scoring with location/name validation; threshold-based selection

**Hint/Keyword Lists:**
- Purpose: Drive discovery and filtering decisions
- Examples: `KEYWORDS`, `COMMON_PATHS`, `DISCOVERY_HINTS`, `GIS_HINTS`, `NOISY_URL_HINTS` in `collect.py`
- Pattern: Module-level constants used across multiple functions

## Entry Points

**fetch_r1_institutions.py:**
- Location: `src/gis_librarians/fetch_r1_institutions.py`
- Triggers: `python src/gis_librarians/fetch_r1_institutions.py`
- Responsibilities: Download Carnegie R1 CSV, build project template

**fetch_arl_members.py:**
- Location: `src/gis_librarians/fetch_arl_members.py`
- Triggers: `python src/gis_librarians/fetch_arl_members.py`
- Responsibilities: Scrape ARL member list, extract library homepages

**enrich_r1_institutions.py:**
- Location: `src/gis_librarians/enrich_r1_institutions.py`
- Triggers: `python src/gis_librarians/enrich_r1_institutions.py [--input] [--output] [--delay] [--limit] [--save-every] [--only-missing]`
- Responsibilities: Query ROR, crawl homepages, write library URLs back to template CSV

**collect.py:**
- Location: `src/gis_librarians/collect.py`
- Triggers: `python src/gis_librarians/collect.py --institutions <csv> --output-dir <dir> [--delay] [--timeout] [--save-every] [--user-agent]`
- Responsibilities: 3-phase link discovery + candidate extraction from library pages

## Error Handling

**Strategy:** Try-except per HTTP call, log to CSV (`fetch_log.csv`), continue processing

**Patterns:**
- `HTTPError`, `URLError` caught specifically in `collect.py`
- Bare `except Exception` in `enrich_r1_institutions.py` (see CONCERNS.md)
- Failures logged with status codes: `"ok"`, `"skipped"`, `"http_error"`, `"url_error"`, `"error"`
- No retry logic or exponential backoff for rate-limited responses

## Cross-Cutting Concerns

**Logging:**
- No logging framework — status written to `output/fetch_log.csv` and stdout print statements
- Each run appends to fetch log

**Validation:**
- URL filtering via hint lists and negative patterns before fetching
- Name/email plausibility checks in `collect.py` (`is_plausible_candidate()`)
- No pre-flight URL validation (see CONCERNS.md)

**Rate Limiting:**
- `--delay` parameter (per-institution delay) in both enrichment and collection scripts
- Inner HTTP calls within a row are not individually rate-limited

---

*Architecture analysis: 2026-03-20*
*Update when major patterns change*
