# AGENTS.md

## Purpose

This repository builds and maintains a public, reproducible directory of GIS and geospatial librarians at Carnegie 2025 Research 1 institutions in the United States.

The project has three outputs:

- a working data collection workflow
- a versioned CSV suitable for GitHub publication
- a public spreadsheet suitable for collaborative review and outreach

## Working Rules

- Treat official institutional pages as the primary source of truth.
- Preserve provenance for every row and every derived field.
- Do not present inferred data as verified data.
- Prefer reproducible scripts over one-off manual edits when a task will recur.
- Keep the raw import, intermediate discovery data, and verified publishable data logically separate.
- Avoid destructive cleanup of collected data unless the reason is documented.

## Source Priority

Use sources in this order unless there is a strong reason not to:

1. Official Carnegie classifications export for the R1 institution universe.
2. Official university library websites, staff directories, subject guide pages, and department pages.
3. Official university profile pages outside the library domain.
4. Public professional pages that link back to the official institution.
5. Mailing lists, conference rosters, and other secondary sources as leads only.

Secondary sources may suggest a candidate, but final verification should land on an official page whenever possible.

## Data Standards

- Canonical schema lives in [data/schema.csv](/Users/timdennis/projects/gis-librarians-library/data/schema.csv).
- Raw Carnegie import belongs in `data/raw/`.
- Institution discovery inputs belong in [data/r1_institutions_template.csv](/Users/timdennis/projects/gis-librarians-library/data/r1_institutions_template.csv).
- Candidate leads from automated collection are not publishable until manually verified.
- If an email address is inferred, label it explicitly as inferred until confirmed.
- If an individual requests removal, honor it and track the opt-out state.

## Expected Workflow

1. Refresh the official R1 list.
2. Enrich institutions with domains and library entry points.
3. Run collection scripts to generate candidate rows.
4. Manually verify candidate identity, role, institution, and source URL.
5. Prepare a cleaned publication dataset.
6. Publish and maintain changelog-style status updates.

## File Conventions

- Put durable project instructions in repo-root documentation.
- Put code in `src/gis_librarians/`.
- Put templates and reusable text assets in `templates/`.
- Put manual search patterns in `queries/`.
- Do not commit secrets, credentials, or private contact notes.

## When Editing

- Update [README.md](/Users/timdennis/projects/gis-librarians-library/README.md) when the operator workflow changes.
- Update [STATUS.md](/Users/timdennis/projects/gis-librarians-library/STATUS.md) when project state changes materially.
- Update the spec if scope, schema, or acceptance criteria change.
- Update the context doc when assumptions, current blockers, or near-term priorities change.

## Definition of Done

A change is complete when:

- the relevant documentation matches reality
- any new script is runnable from the repository root
- outputs and their status are clearly labeled as raw, intermediate, or verified
- important limitations and risks are documented
