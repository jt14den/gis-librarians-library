#!/usr/bin/env python3
"""Search for GIS librarians at unenriched R1 institutions via SerpAPI.

Reads institutions with no Library URL from the R1 template, queries SerpAPI
for each, and writes hits to a CSV for manual review. Results are cached so
interrupted runs can resume without burning additional searches.

Medical and health science schools are skipped by default (no GIS librarians).

Usage:
    export SERPAPI_KEY=your_key_here
    python3 src/gis_librarians/search_gis_librarians.py

    # Dry run — show queries without calling the API:
    python3 src/gis_librarians/search_gis_librarians.py --dry-run

    # Limit to N searches (useful for testing):
    python3 src/gis_librarians/search_gis_librarians.py --limit 10

    # Also search institutions that have a library URL but no directory URL:
    python3 src/gis_librarians/search_gis_librarians.py --include-partial

    # Include medical/health science schools (skipped by default):
    python3 src/gis_librarians/search_gis_librarians.py --include-medical
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

INSTITUTIONS_CSV = Path("data/r1_institutions_template.csv")
CACHE_FILE = Path("output/search_cache.json")
RESULTS_CSV = Path("output/search_results.csv")

SEARCHAPI_ENDPOINT = "https://www.searchapi.io/api/v1/search"

MEDICAL_KEYWORDS = (
    "health science",
    "medical",
    "medicine",
    "health center",
    "pharmacy",
    "dental",
    "nursing",
)
QUERY_TEMPLATE = '"GIS librarian" OR "geospatial librarian" OR "map librarian" "{institution}"'
RESULTS_FIELDNAMES = [
    "Institution",
    "Query",
    "Result Title",
    "Result URL",
    "Result Snippet",
    "Search Status",
]


def is_medical(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in MEDICAL_KEYWORDS)


def load_institutions(include_partial: bool, include_medical: bool) -> list[dict[str, str]]:
    """Return institutions that still need searching."""
    rows = []
    skipped_medical = []
    with INSTITUTIONS_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lib_url = row["Library URL"].strip()
            dir_url = row["Library Directory URL"].strip()
            name = row["Institution"].strip()
            if dir_url:
                continue  # already has a directory URL — skip
            if lib_url and not include_partial:
                continue  # has lib URL but we're not including partials
            if not include_medical and is_medical(name):
                skipped_medical.append(name)
                continue
            rows.append(row)
    if skipped_medical:
        print(f"  Skipping {len(skipped_medical)} medical/health science schools (use --include-medical to search them)")
    return rows


def load_cache() -> dict[str, list[dict]]:
    """Load cached search results keyed by institution name."""
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, list[dict]]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def searchapi_search(query: str, api_key: str) -> list[dict]:
    """Call SearchAPI and return organic results."""
    params = urlencode({
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": 5,
    })
    url = f"{SEARCHAPI_ENDPOINT}?{params}"
    with urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("organic_results", [])


def build_result_rows(institution: str, query: str, results: list[dict], status: str) -> list[dict]:
    if not results:
        return [{
            "Institution": institution,
            "Query": query,
            "Result Title": "",
            "Result URL": "",
            "Result Snippet": "",
            "Search Status": status,
        }]
    rows = []
    for r in results:
        rows.append({
            "Institution": institution,
            "Query": query,
            "Result Title": r.get("title", ""),
            "Result URL": r.get("link", ""),
            "Result Snippet": r.get("snippet", ""),
            "Search Status": status,
        })
    return rows


def write_results(rows: list[dict]) -> None:
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULTS_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print queries without calling the API")
    parser.add_argument("--limit", type=int, default=0, help="Max number of API calls to make (0 = no limit)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls (default: 1.0)")
    parser.add_argument("--include-partial", action="store_true",
                        help="Also search institutions that have a library URL but no directory URL")
    parser.add_argument("--include-medical", action="store_true",
                        help="Include medical/health science schools (skipped by default)")
    args = parser.parse_args()

    api_key = os.environ.get("SEARCHAPI_KEY", "").strip()
    if not api_key and not args.dry_run:
        print("Error: SEARCHAPI_KEY environment variable not set.", file=sys.stderr)
        print("Export it first:  export SEARCHAPI_KEY=your_key_here", file=sys.stderr)
        return 1

    institutions = load_institutions(args.include_partial, args.include_medical)
    cache = load_cache()

    print(f"Institutions to search: {len(institutions)}")
    cached_count = sum(1 for row in institutions if row["Institution"] in cache)
    fresh_needed = len(institutions) - cached_count
    print(f"  {cached_count} already cached, {fresh_needed} need API calls")

    if args.limit and fresh_needed > args.limit:
        print(f"  Limiting to {args.limit} new API calls (--limit)")

    if args.dry_run:
        print("\nDry run — queries that would be sent:")
        for row in institutions:
            name = row["Institution"]
            if name not in cache:
                query = QUERY_TEMPLATE.format(institution=name)
                print(f"  {name!r:60s}  →  {query}")
        return 0

    all_result_rows: list[dict] = []
    api_calls = 0

    for row in institutions:
        name = row["Institution"]
        query = QUERY_TEMPLATE.format(institution=name)

        if name in cache:
            results = cache[name]
            status = "cached"
        else:
            if args.limit and api_calls >= args.limit:
                print(f"  Reached --limit {args.limit}, stopping.")
                break

            print(f"[{api_calls + 1}] Searching: {name}")
            try:
                results = searchapi_search(query, api_key)
                status = "ok" if results else "no_results"
                cache[name] = results
                save_cache(cache)
                api_calls += 1
                if args.delay > 0:
                    time.sleep(args.delay)
            except HTTPError as e:
                print(f"  HTTP {e.code} for {name!r}", file=sys.stderr)
                results = []
                status = f"http_{e.code}"
                cache[name] = results
                save_cache(cache)
                api_calls += 1
            except (URLError, OSError) as e:
                print(f"  Error for {name!r}: {e}", file=sys.stderr)
                results = []
                status = "url_error"
                # Don't cache errors so they can be retried

        all_result_rows.extend(build_result_rows(name, query, results, status))

    write_results(all_result_rows)

    total = len([r for r in all_result_rows if r["Search Status"] != "cached" or r["Result URL"]])
    hits = len([r for r in all_result_rows if r["Result URL"]])
    print(f"\nDone. {api_calls} API calls made.")
    print(f"Results with hits: {len(set(r['Institution'] for r in all_result_rows if r['Result URL']))}")
    print(f"Wrote {len(all_result_rows)} rows to {RESULTS_CSV}")
    print(f"Cache saved to {CACHE_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
