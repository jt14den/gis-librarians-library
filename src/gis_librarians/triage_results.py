#!/usr/bin/env python3
"""Triage search results into tiers for manual review.

Tier 1 — Direct hit: result URL is on an official library domain for that institution.
         These are the highest-confidence leads — open and verify.
Tier 2 — Indirect hit: result mentions the institution + a GIS librarian role but
         URL is a job board, journal, conference, or social site.
         Confirms a position likely exists; needs a fresh search to find the current person.
Tier 3 — Noise: result mentions GIS librarians at other institutions incidentally.
         Low value; skip unless nothing else exists.

Usage:
    python3 src/gis_librarians/triage_results.py
    python3 src/gis_librarians/triage_results.py --tier 1
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

INPUT_CSV = Path("output/search_results.csv")
OUTPUT_CSV = Path("output/search_results_triaged.csv")

# Domains that indicate a direct official library hit
LIBRARY_DOMAIN_PATTERNS = re.compile(
    r"(library\.|lib\.|libguides\.|libweb\.|research\.lib\.|libraries\.)",
    re.IGNORECASE,
)

# Domains that are clearly indirect (job boards, journals, social, etc.)
INDIRECT_DOMAINS = {
    "jobs.code4lib.org",
    "iassistdata.org",
    "lists.clir.org",
    "listserv.uga.edu",
    "crln.acrl.org",
    "journal.calaijol.org",
    "digitalcommons.",
    "researchgate.net",
    "academia.edu",
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "waml.org",
    "connect.ala.org",
    "arcgis.com",
    "esri.com",
    "utppublishing.com",
    "spatial.scholarslab.org",
    "cni.org",
}


def institution_domain_hint(institution: str) -> str:
    """Derive a rough domain fragment from institution name for matching."""
    name = institution.lower()
    # Strip common prefixes
    for prefix in ("the university of ", "university of ", "the ", "university at "):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    # Take first word, strip punctuation
    word = re.split(r"[\s\-&,]", name)[0]
    word = re.sub(r"[^a-z0-9]", "", word)
    return word


def score_result(institution: str, url: str, snippet: str, title: str) -> tuple[int, str]:
    """Return (tier, reason) for a single result row."""
    if not url:
        return 3, "no_url"

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    hint = institution_domain_hint(institution)

    # Tier 1: official library domain that contains institution hint
    if LIBRARY_DOMAIN_PATTERNS.search(domain) and hint in domain:
        return 1, "official_library_domain"

    # Tier 1: libguides always official even if domain hint is fuzzy
    if "libguides." in domain or "libweb." in domain:
        return 1, "libguides"

    # Tier 2: indirect but institution is mentioned in snippet/title
    inst_lower = institution.lower().split()[0]  # first word is usually distinctive
    text = (snippet + " " + title).lower()
    is_indirect = any(d in domain for d in INDIRECT_DOMAINS)
    mentions_inst = hint in text or inst_lower in text

    if is_indirect and mentions_inst:
        return 2, "indirect_with_institution_mention"

    if is_indirect:
        return 3, "indirect_no_institution_mention"

    # Tier 1 fallback: any .edu domain with library hint and institution hint
    if ".edu" in domain and hint in domain and LIBRARY_DOMAIN_PATTERNS.search(url):
        return 1, "edu_library_url"

    # Tier 2 fallback: .edu domain for this institution (non-library page)
    if ".edu" in domain and hint in domain:
        return 2, "edu_non_library"

    return 3, "off_site"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tier", type=int, choices=[1, 2, 3],
                        help="Only show results of this tier")
    args = parser.parse_args()

    rows = list(csv.DictReader(INPUT_CSV.open(encoding="utf-8")))

    # Score every row
    tiered: list[dict] = []
    for row in rows:
        tier, reason = score_result(
            row["Institution"],
            row["Result URL"],
            row["Result Snippet"],
            row["Result Title"],
        )
        tiered.append({**row, "Tier": tier, "Tier Reason": reason})

    # Write full triaged output
    fieldnames = list(tiered[0].keys())
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tiered)

    # Summary by institution — best tier per institution
    by_inst: dict[str, list[dict]] = defaultdict(list)
    for row in tiered:
        by_inst[row["Institution"]].append(row)

    tier1_insts = sorted(
        inst for inst, rows in by_inst.items()
        if any(r["Tier"] == 1 for r in rows)
    )
    tier2_only = sorted(
        inst for inst, rows in by_inst.items()
        if not any(r["Tier"] == 1 for r in rows)
        and any(r["Tier"] == 2 for r in rows)
    )
    tier3_only = sorted(
        inst for inst, rows in by_inst.items()
        if all(r["Tier"] == 3 for r in rows)
    )

    if args.tier is None or args.tier == 1:
        print(f"\n=== TIER 1 — Direct library hits ({len(tier1_insts)} institutions) ===")
        for inst in tier1_insts:
            t1_rows = [r for r in by_inst[inst] if r["Tier"] == 1]
            for r in t1_rows[:1]:
                print(f"\n  {inst}")
                print(f"  {r['Result URL']}")
                print(f"  {r['Result Snippet'][:120]}")

    if args.tier is None or args.tier == 2:
        print(f"\n=== TIER 2 — Indirect hits ({len(tier2_only)} institutions) ===")
        for inst in tier2_only:
            t2_rows = [r for r in by_inst[inst] if r["Tier"] == 2]
            for r in t2_rows[:1]:
                print(f"\n  {inst}")
                print(f"  {r['Result URL']}")
                print(f"  {r['Result Snippet'][:120]}")

    if args.tier is None or args.tier == 3:
        print(f"\n=== TIER 3 — Low signal / noise ({len(tier3_only)} institutions) ===")
        for inst in tier3_only:
            print(f"  {inst}")

    print(f"\nSummary: {len(tier1_insts)} Tier 1 | {len(tier2_only)} Tier 2 only | {len(tier3_only)} Tier 3 only")
    print(f"Full triaged output written to {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
