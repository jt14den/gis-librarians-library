#!/usr/bin/env python3
"""Download the current ARL members page and extract library homepages."""

from __future__ import annotations

import csv
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ARL_URL = "https://www.arl.org/list-of-arl-members/"
USER_AGENT = "Mozilla/5.0"
RAW_OUTPUT = Path("data/raw/arl_members.html")
CSV_OUTPUT = Path("data/reference/arl_members.csv")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_space(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


class ParagraphLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[dict[str, str]] = []
        self._in_paragraph = False
        self._href: str | None = None
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "p":
            self._in_paragraph = True
        if tag == "a" and self._in_paragraph:
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "a" and self._in_paragraph and self._href:
            label = normalize_space(" ".join(self._parts))
            if label and self._href:
                self.entries.append({"ARL Name": label, "Library URL": self._href})
            self._href = None
            self._parts = []
        if tag == "p":
            self._in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not self._href:
            return
        cleaned = normalize_space(html.unescape(data))
        if cleaned:
            self._parts.append(cleaned)


def fetch_html() -> str:
    request = Request(ARL_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    raw_html = fetch_html()
    RAW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT.write_text(raw_html, encoding="utf-8")

    parser = ParagraphLinkParser()
    parser.feed(raw_html)
    rows = []
    for entry in parser.entries:
        if entry["ARL Name"].lower().startswith("interactive map"):
            continue
        rows.append(
            {
                "ARL Name": entry["ARL Name"],
                "Library URL": entry["Library URL"],
                "Source URL": ARL_URL,
            }
        )
    write_csv(CSV_OUTPUT, rows, ["ARL Name", "Library URL", "Source URL"])
    print(f"Wrote {len(rows)} ARL entries to {CSV_OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
