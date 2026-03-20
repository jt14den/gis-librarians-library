# Codebase Structure

**Analysis Date:** 2026-03-20

## Directory Layout

```
gis-librarians-library/
├── src/
│   └── gis_librarians/        # All Python application code
│       ├── collect.py          # Stage 4: candidate extraction (549 lines)
│       ├── enrich_r1_institutions.py  # Stage 3: institution enrichment (474 lines)
│       ├── fetch_arl_members.py       # Stage 2: ARL member scraper (108 lines)
│       └── fetch_r1_institutions.py   # Stage 1: Carnegie R1 downloader (99 lines)
├── data/                       # All data artifacts
│   ├── schema.csv              # Canonical output schema (10 fields)
│   ├── sample_gis_librarians.csv      # Example/starter data
│   ├── r1_institutions_template.csv   # Pipeline working file (enriched in-place)
│   ├── raw/
│   │   ├── carnegie_r1_2025.csv       # Official Carnegie R1 export
│   │   └── arl_members.html           # Raw ARL webpage snapshot
│   └── reference/
│       ├── arl_members.csv            # Parsed ARL member list
│       └── institution_aliases.csv    # Manual institution name mappings
├── output/                     # Collector pipeline outputs (gitignored)
│   ├── raw_candidates.csv      # Latest candidate extraction
│   ├── fetch_log.csv           # Collection run log
│   └── pass1/, pass2/, ...     # Historical checkpoint directories
├── queries/                    # Search templates
│   └── search_queries.txt
├── templates/                  # Outreach assets
│   └── outreach_email.txt
├── docs/                       # Project documentation
│   ├── CONTEXT.md              # Background, approach, known limitations
│   └── SPEC.md                 # Output schema and field definitions
├── .gitignore                  # Excludes output/, __pycache__, .pyc
├── AGENTS.md                   # Project governance & AI agent rules
├── README.md                   # Operator workflow guide
└── STATUS.md                   # Current status & blockers
```

## Directory Purposes

**`src/gis_librarians/`:**
- Purpose: All executable Python modules
- Contains: 4 pipeline stage scripts
- Key files: `collect.py` (main workhorse), `enrich_r1_institutions.py` (most complex)
- Subdirectories: None

**`data/`:**
- Purpose: Persistent data artifacts (source data, working files, reference)
- Contains: CSV files at various stages of the pipeline
- Key files: `r1_institutions_template.csv` (pipeline working file), `schema.csv` (output spec)
- Subdirectories: `raw/` (unprocessed downloads), `reference/` (reference tables)

**`output/`:**
- Purpose: Pipeline outputs from `collect.py` runs (gitignored)
- Contains: `raw_candidates.csv`, `fetch_log.csv`, checkpoint directories
- Committed: No (in `.gitignore`)

**`docs/`:**
- Purpose: Human and AI operator reference documentation
- Key files: `CONTEXT.md` (limitations, approach), `SPEC.md` (schema definitions)

## Key File Locations

**Entry Points:**
- `src/gis_librarians/fetch_r1_institutions.py` — Stage 1: download Carnegie R1 list
- `src/gis_librarians/fetch_arl_members.py` — Stage 2: scrape ARL members
- `src/gis_librarians/enrich_r1_institutions.py` — Stage 3: enrich with library URLs
- `src/gis_librarians/collect.py` — Stage 4: extract GIS librarian candidates

**Configuration:**
- `.gitignore` — Excludes output/, __pycache__, *.pyc, .DS_Store

**Core Logic:**
- `src/gis_librarians/collect.py` — Keyword matching, HTML parsing, candidate extraction
- `src/gis_librarians/enrich_r1_institutions.py` — ROR API querying, scoring, URL discovery

**Data:**
- `data/r1_institutions_template.csv` — Main working file (enriched in-place by stage 3)
- `data/reference/institution_aliases.csv` — Manual name mappings for cross-source matching
- `data/schema.csv` — Canonical output schema

**Documentation:**
- `README.md` — Step-by-step operator workflow
- `docs/CONTEXT.md` — Background and known limitations
- `AGENTS.md` — AI agent governance rules

## Naming Conventions

**Files:**
- `snake_case.py` for all Python modules
- Verb-first naming: `fetch_*`, `enrich_*`, `collect`

**Directories:**
- Lowercase, plural where appropriate: `docs/`, `queries/`, `templates/`
- Semantic names matching pipeline stage: `raw/`, `reference/`, `output/`

**CSV Files:**
- Lowercase with underscores: `raw_candidates.csv`, `fetch_log.csv`, `arl_members.csv`
- Template files include explicit stage: `r1_institutions_template.csv`

## Where to Add New Code

**New pipeline stage:**
- Implementation: `src/gis_librarians/<verb>_<subject>.py`
- Follow existing `main() → sys.exit()` pattern with `argparse`
- Output: write to `output/` or `data/` depending on type

**New data source:**
- Fetcher: `src/gis_librarians/fetch_<source>.py`
- Reference output: `data/reference/<source>.csv`
- Raw output: `data/raw/<source>.<ext>`

**New reference table:**
- File: `data/reference/<name>.csv`
- Reference in: whichever enrichment module needs it

**Utilities:**
- Not yet extracted — shared helpers like `write_csv()` and `normalize_space()` are currently duplicated across modules (see CONCERNS.md)
- Future: `src/gis_librarians/utils.py`

## Special Directories

**`output/`:**
- Purpose: Pipeline run artifacts (candidates, logs, checkpoints)
- Source: Generated by `collect.py` and `enrich_r1_institutions.py` runs
- Committed: No

**`output/pass*/`:**
- Purpose: Historical checkpoint directories from past collector runs
- Source: Auto-created by `collect.py` checkpoint saves
- Committed: No

---

*Structure analysis: 2026-03-20*
*Update when directory structure changes*
