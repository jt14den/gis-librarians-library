# GIS Librarian Directory Spec

## Objective

Build a reproducible, maintainable directory of GIS and geospatial librarians at Carnegie 2025 Research 1 institutions using public data and explicit provenance.

## Scope

In scope:

- Carnegie 2025 Research 1 institutions
- library employees or affiliates whose public role materially includes GIS, geospatial data, maps, spatial data, geodata, or closely related work
- public professional information suitable for institutional discovery and networking
- scripts and workflows that support repeatable collection and verification

Out of scope:

- private contact details
- speculative role assignments without supporting evidence
- non-R1 institutions unless the project scope is explicitly expanded
- publication of unverified machine-extracted leads as final records

## Primary Deliverables

- Official R1 institution source file
- Institution enrichment template with library URLs
- Raw candidate discovery output
- Verified GIS librarian dataset
- Public-facing spreadsheet and mirrored CSV
- Documentation for workflow, status, and outreach

## Data Model

The publishable schema is defined in [data/schema.csv](/Users/timdennis/projects/gis-librarians-library/data/schema.csv).

Required publication fields:

- `Name`
- `Title/Role`
- `Institution`
- `Profile URL`
- `Verification Source`
- `Last-Checked Date`

Preferred fields:

- `Department/Unit`
- `Email`
- `Notes`
- `Consent/Opt-Out`

Field rules:

- `Verification Source` must describe the specific source used to verify the record.
- `Last-Checked Date` must be an explicit date in `YYYY-MM-DD` format.
- `Consent/Opt-Out` must record removal requests or inclusion constraints.
- `Email` must be blank or marked inferred until verified from a public official source.

## Source Requirements

- The institution universe must come from the official Carnegie 2025 R1 export.
- Verified person-level records should rely on official institutional pages whenever possible.
- Secondary sources may be used to discover leads but should not be the only evidence for publication unless documented as an exception.

## Processing Stages

### Stage 1: Institution import

- Fetch official Carnegie R1 data.
- Preserve the raw export unmodified.
- Generate a project template with enrichment columns.

### Stage 2: Institution enrichment

- Add institution domain.
- Add primary library URL.
- Add known directory or subject guide entry points when available.

### Stage 3: Candidate discovery

- Crawl or fetch likely staff, directory, and guide pages.
- Extract GIS-related candidate signals.
- Save raw candidate rows and fetch logs.

### Stage 4: Manual verification

- Confirm person, role, and institution match.
- Confirm or remove extracted email addresses.
- Remove false positives and duplicates.
- Add provenance and last-checked date.

### Stage 5: Publication

- Export a clean CSV.
- Publish to a shared spreadsheet.
- Preserve source/provenance columns.

## Acceptance Criteria

The project is meeting the spec when:

- the full 2025 Carnegie R1 institution list is present locally
- each institution has a place in the enrichment template
- collection outputs are reproducible from scripts in `src/gis_librarians/`
- verified records are distinguishable from raw candidates
- each published record includes provenance and a last-checked date
- privacy and opt-out handling are documented and operationalized

## Non-Functional Requirements

- Reproducible: a new contributor can regenerate core inputs from the repo.
- Traceable: every published record can be traced back to a source.
- Conservative: ambiguous machine output stays out of the final directory.
- Maintainable: scripts should use modest dependencies and clear inputs/outputs.
- Ethical: only public information is used, and opt-outs are respected.
