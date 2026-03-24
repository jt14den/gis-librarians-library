# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A reproducible ETL pipeline that discovers and publishes a directory of GIS/geospatial librarians at Carnegie R1 research institutions in the US. Pure Python 3.10+ stdlib only — no external dependencies, no package manager, no virtual environment needed.

## Running the Pipeline

The pipeline has 4 sequential stages. Each is a standalone script run directly:

```bash
# Stage 1: Download official Carnegie R1 list → data/raw/carnegie_r1_2025.csv + data/r1_institutions_template.csv
python3 src/gis_librarians/fetch_r1_institutions.py

# Stage 2: Scrape ARL member list → data/reference/arl_members.csv
python3 src/gis_librarians/fetch_arl_members.py

# Stage 3: Enrich institutions with domains and library URLs (enriches data/r1_institutions_template.csv in-place)
python3 src/gis_librarians/enrich_r1_institutions.py --only-missing
# Other flags: --input, --output, --delay, --limit, --save-every

# Stage 4: Collect GIS librarian candidates from library pages → output/raw_candidates.csv + output/fetch_log.csv
python3 src/gis_librarians/collect.py \
  --institutions data/r1_institutions_template.csv \
  --output-dir output
# Other flags: --delay, --timeout, --save-every, --user-agent
```

There is no test suite. Validate results by reviewing `output/raw_candidates.csv` and `output/fetch_log.csv` manually.

## Architecture

**Pattern:** Sequential ETL pipeline with file-based state. Each stage reads and writes CSVs; no database.

**Data flow:**
1. `fetch_r1_institutions.py` → Carnegie API → `data/raw/carnegie_r1_2025.csv`
2. `fetch_arl_members.py` → ARL website → `data/reference/arl_members.csv`
3. `enrich_r1_institutions.py` → ROR API + web crawl → enriches `data/r1_institutions_template.csv` with `domain`, `website_url`, `library_url`, `library_directory_url`
4. `collect.py` → crawls library staff/directory pages → `output/raw_candidates.csv`

**Resumability:** Both Stage 3 and Stage 4 support `--save-every N` checkpoints and `--only-missing` / incremental modes to resume interrupted runs safely.

**Key abstractions in the code:**
- `HTMLParser` subclasses (`LinkParser`, `LinkTextParser`, `ParagraphLinkParser`) for HTML extraction
- `Candidate` dataclass in `collect.py` for structured librarian records
- Scoring functions (`score_ror_item()`, `select_arl_match()`) for fuzzy institution matching across data sources
- Keyword/hint lists (`KEYWORDS`, `DISCOVERY_HINTS`, `NOISY_URL_HINTS`) that drive discovery decisions

## Data Layout

| Path | Purpose |
|------|---------|
| `data/r1_institutions_template.csv` | Main working file — enriched in-place by Stage 3 |
| `data/raw/carnegie_r1_2025.csv` | Official Carnegie export (do not edit) |
| `data/reference/arl_members.csv` | ARL member reference (do not edit) |
| `data/reference/institution_aliases.csv` | Manual name mappings for fuzzy matching |
| `data/schema.csv` | Canonical output schema (10 fields) |
| `data/sample_gis_librarians.csv` | Example verified records |
| `output/` | Collector outputs — gitignored; historical passes in `output/pass1/`–`output/pass4/` |

## Conventions (from AGENTS.md)

- Treat official institutional pages as the primary source of truth; preserve provenance on every row
- Keep raw, intermediate, and verified data logically separate
- Prefer reproducible scripts over one-off manual edits
- Script names use verb-first convention: `fetch_*`, `enrich_*`, `collect`
- New code goes in `src/gis_librarians/`; reference data in `data/reference/`; outreach assets in `templates/`

## Known Technical Debt

- `write_csv()` and `normalize_space()` are duplicated across modules
- No per-request rate limiting inside enrichment inner loops (outer `--delay` only)
- Broad `except Exception: pass` in enrichment hides DNS/timeout failures
- No retry logic for 429/401 responses
- Multi-person directory pages: flattened text parsing produces mixed results when multiple people appear in dense paragraphs (see `.planning/codebase/CONCERNS.md`)

## Current Status

187 R1 institutions in scope. As of March 2026: ~79 enriched with domains/library URLs, ~58 with directory URLs. See `STATUS.md` for current numbers. Pass 4 of the collector is the cleanest output; lives in `output/pass4/raw_candidates.csv`.
