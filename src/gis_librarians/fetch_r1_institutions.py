#!/usr/bin/env python3
"""Download the official Carnegie 2025 R1 institution list and build a project template."""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CARNEGIE_BASE_URL = "https://carnegieclassifications.acenet.edu/institutions/"
RAW_OUTPUT = Path("data/raw/carnegie_r1_2025.csv")
TEMPLATE_OUTPUT = Path("data/r1_institutions_template.csv")
USER_AGENT = "Mozilla/5.0"


def fetch_r1_csv() -> str:
    params = urlencode(
        {
            "inst": "",
            "research2025[]": "1",
            "format": "csv",
            "descr": "Research 1 institutions",
        },
        doseq=True,
    )
    request = Request(f"{CARNEGIE_BASE_URL}?{params}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig", errors="replace")


def read_rows(csv_text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(csv_text)))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_template_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "Institution": row["name"],
            "Institution Domain": "",
            "Institution Website": "",
            "Institution Match Source": "",
            "ROR ID": "",
            "Library URL": "",
            "Library URL Source": "",
            "Library Directory URL": "",
            "Library Directory Source": "",
            "Carnegie UnitID": row["unitid"],
            "City": row["city"],
            "State": row["state"],
            "Control": row["control"],
            "Research Activity Designation": row["Research Activity Designation"],
            "Notes": "Imported from official Carnegie 2025 R1 CSV",
        }
        for row in rows
    ]


def main() -> int:
    csv_text = fetch_r1_csv()
    rows = read_rows(csv_text)
    write_csv(RAW_OUTPUT, rows, list(rows[0].keys()))
    write_csv(
        TEMPLATE_OUTPUT,
        build_template_rows(rows),
        [
            "Institution",
            "Institution Domain",
            "Institution Website",
            "Institution Match Source",
            "ROR ID",
            "Library URL",
            "Library URL Source",
            "Library Directory URL",
            "Library Directory Source",
            "Carnegie UnitID",
            "City",
            "State",
            "Control",
            "Research Activity Designation",
            "Notes",
        ],
    )
    print(f"Wrote {len(rows)} R1 institutions to {TEMPLATE_OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
