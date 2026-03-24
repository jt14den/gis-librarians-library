# GIS Librarian Directory Context

## Current State

This repository started as an implementation of a planning memo for a public directory of GIS librarians at R1 institutions.

As of March 13, 2026:

- the repository contains a canonical schema
- the repository contains a sample CSV derived from the planning memo
- the official Carnegie 2025 Research 1 institution list has been downloaded
- a generated institution template with 187 R1 institutions exists
- an ARL member reference file and manual institution alias file exist for cross-source matching
- the institution enrichment workflow is active and has partially populated the R1 template
- the collector has been upgraded from a rough first pass into a checkpointed lead-generation tool

Current enrichment coverage in [data/r1_institutions_template.csv](/Users/timdennis/projects/gis-librarians-library/data/r1_institutions_template.csv):

- `Institution Domain`: 79 / 187
- `Institution Website`: 79 / 187
- `Library URL`: 72 / 187
- `Library Directory URL`: 58 / 187
- ARL-backed library URL matches: 19

## Current Files That Matter Most

- [README.md](/Users/timdennis/projects/gis-librarians-library/README.md)
- [STATUS.md](/Users/timdennis/projects/gis-librarians-library/STATUS.md)
- [data/raw/carnegie_r1_2025.csv](/Users/timdennis/projects/gis-librarians-library/data/raw/carnegie_r1_2025.csv)
- [data/r1_institutions_template.csv](/Users/timdennis/projects/gis-librarians-library/data/r1_institutions_template.csv)
- [data/reference/arl_members.csv](/Users/timdennis/projects/gis-librarians-library/data/reference/arl_members.csv)
- [data/reference/institution_aliases.csv](/Users/timdennis/projects/gis-librarians-library/data/reference/institution_aliases.csv)
- [data/schema.csv](/Users/timdennis/projects/gis-librarians-library/data/schema.csv)
- [src/gis_librarians/fetch_r1_institutions.py](/Users/timdennis/projects/gis-librarians-library/src/gis_librarians/fetch_r1_institutions.py)
- [src/gis_librarians/fetch_arl_members.py](/Users/timdennis/projects/gis-librarians-library/src/gis_librarians/fetch_arl_members.py)
- [src/gis_librarians/enrich_r1_institutions.py](/Users/timdennis/projects/gis-librarians-library/src/gis_librarians/enrich_r1_institutions.py)
- [src/gis_librarians/collect.py](/Users/timdennis/projects/gis-librarians-library/src/gis_librarians/collect.py)
- [output/pass4/raw_candidates.csv](/Users/timdennis/projects/gis-librarians-library/output/pass4/raw_candidates.csv)
- [output/pass4/fetch_log.csv](/Users/timdennis/projects/gis-librarians-library/output/pass4/fetch_log.csv)

## Working Assumptions

- The official Carnegie R1 export defines the institution universe.
- The project should prioritize official library pages over social or third-party profiles.
- ARL is a useful secondary source for library homepages, but not for defining scope.
- Automation will help discover candidates but will not be sufficient for publication-quality data.
- The final dataset should remain lightweight enough to maintain with ordinary CSV and spreadsheet tooling.

## Known Gaps

- 108 institutions still lack a populated `Institution Domain`.
- 115 institutions still lack a `Library URL`.
- 129 institutions still lack a `Library Directory URL`.
- The collector still struggles on multi-person directory pages where flattened text mixes several staff entries together.
- Search-engine-guided discovery is not yet integrated into code.
- Publication-ready verified data has not been created yet.

## Risks

- Institutional websites are highly inconsistent in structure and terminology.
- Rate limiting and protected staff pages (`429`, `401`) reduce collector coverage on some institutions.
- Some relevant roles may not use the phrase "GIS Librarian" even when functionally equivalent.
- Some institutions may centralize GIS work outside the library, creating ambiguous inclusion decisions.
- Staff listings and guides change frequently, so verification dates matter.

## Near-Term Priorities

1. Continue enriching the remaining R1 institutions with domains, library homepages, and directory entry points.
2. Improve collector precision on staff directory pages by parsing person cards or profile blocks instead of flattened page text.
3. Run a broader collector pass on the enriched subset once extraction quality is acceptable.
4. Establish a verified output file separate from raw collector output.
5. Define the review process for duplicates, edge cases, and opt-outs.

## Operational Notes

- The Carnegie site requires a browser-like user agent for scripted downloads.
- ARL overlays are currently improving library URL coverage and should remain part of the enrichment workflow.
- Collector outputs should be treated as leads, not final records.
- The best current collector snapshot is in `output/pass4/`; it is materially cleaner than earlier passes but still requires manual review.
- The sample dataset is useful as a shape example, not as a final publication artifact.
