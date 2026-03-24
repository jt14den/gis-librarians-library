# GIS Librarians Library

This repository turns the GIS librarian directory plan into a runnable workflow.

## What is here

- `data/schema.csv`: canonical spreadsheet columns.
- `data/sample_gis_librarians.csv`: starter/example rows based on the planning document.
- `data/r1_institutions_template.csv`: input template for the Carnegie R1 institution list.
- `data/raw/carnegie_r1_2025.csv`: raw official Carnegie export for Research 1 institutions.
- `data/reference/arl_members.csv`: current ARL member library URLs for overlay matching.
- `data/reference/institution_aliases.csv`: manual institution-name aliases for cross-source matching.
- `queries/search_queries.txt`: reusable search templates for manual discovery.
- `templates/outreach_email.txt`: outreach message with opt-out language.
- `src/gis_librarians/fetch_r1_institutions.py`: downloads the official 2025 Carnegie R1 list and builds the project template.
- `src/gis_librarians/fetch_arl_members.py`: downloads and extracts the ARL member library list.
- `src/gis_librarians/enrich_r1_institutions.py`: enriches the R1 template with official institution websites, domains, library URLs, and likely directory URLs.
- `src/gis_librarians/collect.py`: dependency-light collector for staff pages and subject guides.

## Workflow

1. Refresh the official R1 list.
2. Run the enrichment pass to fill institution domains and likely library entry points.
3. Run the collector against the institution list.
4. Review `raw_candidates.csv` and `fetch_log.csv` in the output directory.
5. Manually verify names, titles, profile URLs, and email addresses.
6. Publish the verified sheet to Google Sheets and mirror the CSV in GitHub.

## Refreshing the R1 list

```bash
python3 src/gis_librarians/fetch_r1_institutions.py
```

This writes:

- [data/raw/carnegie_r1_2025.csv](/Users/timdennis/projects/gis-librarians-library/data/raw/carnegie_r1_2025.csv)
- [data/r1_institutions_template.csv](/Users/timdennis/projects/gis-librarians-library/data/r1_institutions_template.csv)

The generated template preserves the official institution list and adds project-specific fields for library discovery.

## Enriching the R1 template

```bash
python3 src/gis_librarians/fetch_arl_members.py
python3 src/gis_librarians/enrich_r1_institutions.py --only-missing
```

This step uses:

- the ROR API for institution websites and domains
- the ARL member list for curated library homepage overlays
- institution homepage discovery for additional library and directory URLs

It populates:

- `Institution Domain`
- `Institution Website`
- `Institution Match Source`
- `ROR ID`
- `Library URL`
- `Library URL Source`
- `Library Directory URL`
- `Library Directory Source`

Use `--save-every N` to checkpoint progress during long runs.

## Collector usage

```bash
python3 src/gis_librarians/collect.py \
  --institutions data/r1_institutions_template.csv \
  --output-dir output
```

The collector:

- fetches likely directory and guide pages for each institution
- scans page text for GIS, geospatial, maps, and spatial keywords
- extracts nearby emails and candidate profile links
- writes a raw candidate file for manual verification

## Notes

- The sample data is illustrative and should not be treated as fully verified production data.
- Inferred emails should remain flagged until confirmed from an official source.
- The script is intentionally conservative; it is designed to produce leads, not final records.
