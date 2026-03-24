# Project Status

## Completed

- Created the canonical directory schema.
- Added a sample spreadsheet CSV from the planning document.
- Added a reproducible script to download the official 2025 Carnegie R1 list.
- Added a reproducible script to download the ARL member library list.
- Added a manual alias file for cross-source institution name matching.
- Generated an R1 institution input template from the official Carnegie data.
- Added a resumable enrichment script for official domains, institution websites, library URLs, and likely directory URLs.
- Added reusable search query templates for manual discovery.
- Added an outreach email template with opt-out language.
- Implemented a checkpointed collector script that fetches likely library pages and writes raw candidate output.
- Tightened collector discovery and extraction to reduce homepage, database, and map-app false positives.
- Produced a cleaner test collector snapshot in [output/pass4/raw_candidates.csv](/Users/timdennis/projects/gis-librarians-library/output/pass4/raw_candidates.csv).

## Pending

- Continue enriching the remaining R1 institutions with library homepages and likely directory URLs.
- Improve collector precision on multi-person directory pages.
- Run the collector across the enriched subset at broader scale.
- Manually verify candidates and remove false positives.
- Publish the verified directory to Google Sheets and a versioned CSV.

## Current Risks

- Library sites vary heavily, so automated extraction will miss some institutions and produce false positives.
- Search-engine-assisted discovery is still a manual step.
- Sample rows should be rechecked before public release.
- ARL overlays are now contributing library URLs for matched institutions and should remain in the enrichment workflow.
- Current enrichment coverage is 79 institution domains, 79 institution websites, 72 library URLs, and 58 library directory URLs out of 187 R1 institutions.
- The collector is now useful for lead generation, but it still needs better segmentation of multi-person directory pages before large-scale harvesting.
