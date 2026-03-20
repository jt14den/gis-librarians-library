# External Integrations

**Analysis Date:** 2026-03-20

## APIs & External Services

**Research Organization Registry (ROR) API:**
- ROR — Institution website and domain discovery via fuzzy name matching
  - Endpoint: `https://api.ror.org/v2/organizations?query=`
  - Used in: `src/gis_librarians/enrich_r1_institutions.py`
  - Auth: None (public API, no key required)
  - Timeout: 12 seconds (JSON_TIMEOUT constant)
  - Rate limits: Not formally documented; handled via `--delay` CLI arg (default 0.2s)

**Carnegie Classifications:**
- Carnegie Classifications — Official R1 institution list
  - Endpoint: `https://carnegieclassifications.acenet.edu/institutions/`
  - Used in: `src/gis_librarians/fetch_r1_institutions.py`
  - Auth: None (public data export)
  - Format: CSV download with filter parameters

**ARL Website:**
- Association of Research Libraries — Library homepage URLs
  - URL: `https://www.arl.org/list-of-arl-members/`
  - Used in: `src/gis_librarians/fetch_arl_members.py`
  - Auth: None (public webpage)
  - Parsing: HTML scraping of paragraph-enclosed links

## Data Storage

**Databases:**
- None — all data stored as CSV files on local disk

**File Storage:**
- Local filesystem only
  - Input data: `data/` directory
  - Output data: `output/` directory (gitignored)

**Caching:**
- None — each run re-fetches unless `--only-missing` flag used

## Authentication & Identity

**Auth Provider:**
- None — all external APIs are public

## Monitoring & Observability

**Error Tracking:**
- CSV-based: `output/fetch_log.csv` records all HTTP fetch outcomes
  - Fields: institution, url, status, detail
  - Status values: `"ok"`, `"skipped"`, `"http_error"`, `"url_error"`, `"error"`

**Analytics:**
- None

**Logs:**
- stdout/stderr (print statements only)
- `output/fetch_log.csv` (structured fetch log)

## CI/CD & Deployment

**Hosting:**
- Not applicable — operator-run local scripts

**CI Pipeline:**
- None

## Environment Configuration

**Development:**
- No environment variables required
- No secrets or API keys needed
- All configuration via CLI arguments

**Production:**
- Not applicable — runs locally as operator tool

## Web Scraping Targets

**Institution Library Websites:**
- Target: Library homepage → staff/directory pages
- Discovery: Common path probing (`/staff`, `/directory`, `/about/staff`, etc.)
- User-Agent: `"GISLibrarianCollector/0.1 (research project; https://example.org/contact)"` (default)
- Configurable via `--user-agent` in `collect.py`
- Timeout: 20 seconds default (`--timeout`)
- Delay: 1.0 second between institutions (`--delay`)

**Common Discovery Paths (from `src/gis_librarians/collect.py`):**
- `/staff`, `/directory`, `/people`, `/about/staff`
- `/services/gis`, `/gis`, `/maps`, `/research`
- `/subjects/gis`, `/guides/gis`

## Webhooks & Callbacks

**Incoming:** None
**Outgoing:** None

---

*Integration audit: 2026-03-20*
*Update when adding/removing external services*
