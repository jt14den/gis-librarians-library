#!/usr/bin/env python3
"""Enrich Carnegie R1 institutions with official domains and library URLs."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

ROR_API_URL = "https://api.ror.org/v2/organizations?query="
USER_AGENT = "Mozilla/5.0"
JSON_TIMEOUT = 12
HTML_TIMEOUT = 10
COMMON_LIBRARY_HOSTS = ("library", "libraries", "lib")
COMMON_DIRECTORY_HINTS = ("staff", "directory", "people", "subject", "liaison", "research-help")
LIBRARY_HINTS = (
    " library",
    " libraries",
    "university library",
    "university libraries",
    "campus library",
    "visit library",
)
NAME_SUFFIXES = (
    " campus immersion",
    " main campus",
)
SKIP_LINK_PREFIXES = ("#", "javascript:", "mailto:", "tel:")
NOISY_PATH_HINTS = ("news", "story", "stories", "events", "calendar", "article", "node")
NOISY_LABEL_HINTS = ("skip to", "main content", "read more", "learn more")
WHITESPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
ALIASES_PATH = Path("data/reference/institution_aliases.csv")
ARL_PATH = Path("data/reference/arl_members.csv")


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if tag == "a":
            self._current_href = dict(attrs).get("href")
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "a" and self._current_href:
            self.links.append((self._current_href, normalize_space(" ".join(self._parts))))
            self._current_href = None
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._current_href is None:
            return
        cleaned = normalize_space(html.unescape(data))
        if cleaned:
            self._parts.append(cleaned)


def normalize_space(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_name(value: str) -> str:
    return NON_ALNUM_RE.sub(" ", value.lower()).strip()


def compress_name(value: str) -> str:
    return normalize_name(value).replace(" ", "")


def name_variants(name: str) -> list[str]:
    variants = [name]
    lower = name.lower()
    for suffix in NAME_SUFFIXES:
        if lower.endswith(suffix):
            variants.append(name[: -len(suffix)])
    if "the university of " in lower:
        variants.append(re.sub(r"^The ", "", name, flags=re.IGNORECASE))
    return list(dict.fromkeys(v.strip() for v in variants if v.strip()))


def read_optional_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=JSON_TIMEOUT) as response:
        return json.load(response)


def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=HTML_TIMEOUT) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def select_ror_match(row: dict[str, str]) -> tuple[dict | None, str]:
    target_name = row["Institution"]
    target_norm = normalize_name(target_name)
    target_compact = compress_name(target_name)
    best_item: dict | None = None
    best_score = -1
    best_query = ""

    for variant in name_variants(target_name):
        payload = fetch_json(f"{ROR_API_URL}{quote(variant)}")
        for item in payload.get("items", []):
            score = score_ror_item(row, item, target_norm, target_compact)
            if score > best_score:
                best_item = item
                best_score = score
                best_query = variant
        if best_score >= 120:
            break

    if best_score < 40:
        return None, ""
    return best_item, best_query


def score_ror_item(row: dict[str, str], item: dict, target_norm: str, target_compact: str) -> int:
    score = 0
    item_names = [entry.get("value", "") for entry in item.get("names", [])]
    normalized_names = [normalize_name(name) for name in item_names if name]
    compact_names = [name.replace(" ", "") for name in normalized_names]

    if target_norm in normalized_names:
        score += 100
    if target_compact in compact_names:
        score += 50
    if any(target_norm in name or name in target_norm for name in normalized_names if name):
        score += 20

    state = row.get("State", "")
    city = row.get("City", "")
    for location in item.get("locations", []):
        details = location.get("geonames_details", {})
        subdivision_name = (details.get("country_subdivision_name") or "").lower()
        subdivision_code = (details.get("country_subdivision_code") or "").lower()
        location_name = (details.get("name") or "").lower()
        if details.get("country_code") == "US":
            score += 10
        if state and (
            subdivision_name == state.lower()
            or subdivision_code == state.lower()
        ):
            score += 15
        if city and location_name == city.lower():
            score += 10

    if any(item_type == "education" for item_type in item.get("types", [])):
        score += 10
    return score


def first_website(item: dict) -> str:
    for link in item.get("links", []):
        if link.get("type") == "website" and link.get("value"):
            return link["value"]
    return ""


def extract_domain(item: dict, website: str) -> str:
    domains = item.get("domains", [])
    if domains:
        return domains[0]
    parsed = urlparse(website)
    return parsed.netloc.removeprefix("www.")


def build_alias_map(path: Path) -> dict[str, list[str]]:
    alias_map: dict[str, list[str]] = {}
    for row in read_optional_csv(path):
        canonical = row.get("Canonical Institution", "").strip()
        alias = row.get("Alias", "").strip()
        if canonical and alias:
            alias_map.setdefault(canonical, []).append(alias)
    return alias_map


def canonical_variants(row: dict[str, str], alias_map: dict[str, list[str]]) -> list[str]:
    variants = name_variants(row["Institution"])
    variants.extend(alias_map.get(row["Institution"], []))
    return list(dict.fromkeys(v for v in variants if v))


def strip_library_words(value: str) -> str:
    normalized = normalize_name(value)
    for token in (
        " libraries and cultural resources",
        " library system",
        " libraries",
        " library",
    ):
        if normalized.endswith(token):
            normalized = normalized[: -len(token)].strip()
    return normalized


def select_arl_match(row: dict[str, str], arl_rows: list[dict[str, str]], alias_map: dict[str, list[str]]) -> dict[str, str] | None:
    variants = canonical_variants(row, alias_map)
    normalized_variants = {normalize_name(v) for v in variants}
    compact_variants = {v.replace(" ", "") for v in normalized_variants}

    best_row: dict[str, str] | None = None
    best_score = -1
    for arl_row in arl_rows:
        arl_name = arl_row.get("ARL Name", "")
        base_name = strip_library_words(arl_name)
        compact_name = base_name.replace(" ", "")
        score = 0
        if base_name in normalized_variants:
            score += 100
        if compact_name in compact_variants:
            score += 60
        if any(base_name in variant or variant in base_name for variant in normalized_variants):
            score += 25
        if row.get("State") and row["State"].lower() in arl_name.lower():
            score += 5
        if score > best_score:
            best_score = score
            best_row = arl_row
    if best_score < 60:
        return None
    return best_row


def choose_library_link(homepage_url: str, homepage_html: str, domain: str) -> tuple[str, str]:
    parser = LinkParser()
    parser.feed(homepage_html)
    best_url = ""
    best_reason = ""
    best_score = -1

    for href, label in parser.links:
        if not href:
            continue
        if href.startswith(SKIP_LINK_PREFIXES):
            continue
        absolute = urljoin(homepage_url, href)
        parsed = urlparse(absolute)
        host = parsed.netloc.removeprefix("www.")
        if parsed.scheme not in {"http", "https"}:
            continue
        if not parsed.netloc:
            continue
        score = 0
        combined = f"{label} {absolute}".lower()
        lower_label = label.lower()
        if domain and domain not in host and not host.endswith(f".{domain}"):
            continue
        if any(host == f"{prefix}.{domain}" for prefix in COMMON_LIBRARY_HOSTS if domain):
            score += 100
        if any(f"{prefix}." in host for prefix in COMMON_LIBRARY_HOSTS):
            score += 50
        if any(hint in lower_label for hint in LIBRARY_HINTS):
            score += 30
        if "/library" in parsed.path or "/libraries" in parsed.path:
            score += 20
        if not (
            any(host == f"{prefix}.{domain}" for prefix in COMMON_LIBRARY_HOSTS if domain)
            or any(hint in combined for hint in LIBRARY_HINTS)
            or "/library" in parsed.path
            or "/libraries" in parsed.path
        ):
            continue
        if any(token in parsed.path.lower() for token in NOISY_PATH_HINTS):
            score -= 40
        if any(token in lower_label for token in NOISY_LABEL_HINTS):
            score -= 80
        if parsed.fragment and not parsed.path.strip("/"):
            score -= 100
        if score > best_score:
            best_score = score
            best_url = absolute
            best_reason = f"homepage link: {label or absolute}"

    return best_url, best_reason


def candidate_library_hosts(domain: str) -> list[str]:
    return [f"https://{prefix}.{domain}" for prefix in COMMON_LIBRARY_HOSTS if domain]


def url_reachable(url: str) -> bool:
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=HTML_TIMEOUT) as response:
            return response.status < 400
    except Exception:
        return False


def discover_library_url(website: str, domain: str) -> tuple[str, str]:
    for candidate in candidate_library_hosts(domain):
        if url_reachable(candidate):
            return candidate, f"common library host: {candidate}"

    try:
        homepage_html = fetch_html(website)
        library_url, reason = choose_library_link(website, homepage_html, domain)
        if library_url:
            return library_url, reason
    except Exception:
        pass
    return "", ""


def discover_directory_url(library_url: str) -> tuple[str, str]:
    if not library_url:
        return "", ""
    try:
        html_body = fetch_html(library_url)
    except Exception:
        return "", ""
    parser = LinkParser()
    parser.feed(html_body)
    library_host = urlparse(library_url).netloc.removeprefix("www.")

    best_url = ""
    best_score = -1
    best_reason = ""
    for href, label in parser.links:
        if not href or href.startswith(SKIP_LINK_PREFIXES):
            continue
        absolute = urljoin(library_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        host = parsed.netloc.removeprefix("www.")
        if library_host and host and host != library_host:
            continue
        combined = f"{label} {absolute}".lower()
        score = 0
        if any(hint in combined for hint in COMMON_DIRECTORY_HINTS):
            score += 20
        if "/directory" in parsed.path or "/staff" in parsed.path:
            score += 30
        if "/subject" in parsed.path or "/liaison" in parsed.path:
            score += 20
        if absolute.rstrip("/") == library_url.rstrip("/"):
            score -= 25
        if "browzine" in combined:
            score -= 50
        if score <= 0:
            continue
        if score > best_score:
            best_score = score
            best_url = absolute
            best_reason = f"library link: {label or absolute}"
    return best_url, best_reason


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/r1_institutions_template.csv", type=Path)
    parser.add_argument("--output", default="data/r1_institutions_template.csv", type=Path)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--save-every", type=int, default=10)
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Skip rows that already have domain, website, library URL, and directory URL",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = read_rows(args.input)
    alias_map = build_alias_map(ALIASES_PATH)
    arl_rows = read_optional_csv(ARL_PATH)
    if args.only_missing:
        candidate_rows = [
            row
            for row in rows
            if not (
                row.get("Institution Domain")
                and row.get("Institution Website")
                and row.get("Library URL")
                and row.get("Library Directory URL")
            )
        ]
    else:
        candidate_rows = rows

    if args.limit > 0:
        rows_to_process = candidate_rows[: args.limit]
    else:
        rows_to_process = candidate_rows

    fieldnames = list(rows[0].keys())

    for index, row in enumerate(rows_to_process, start=1):
        try:
            item = None
            query = ""
            if not (row.get("Institution Domain") and row.get("Institution Website") and row.get("ROR ID")):
                item, query = select_ror_match(row)
                if item:
                    website = first_website(item)
                    domain = extract_domain(item, website)
                    row["Institution Website"] = website
                    row["Institution Domain"] = domain
                    row["Institution Match Source"] = f"ROR query: {query}"
                    row["ROR ID"] = item.get("id", "")
            arl_match = select_arl_match(row, arl_rows, alias_map)
            if arl_match and not row.get("Library URL"):
                row["Library URL"] = arl_match.get("Library URL", "")
                row["Library URL Source"] = f"ARL member list: {arl_match.get('ARL Name', '')}"
            website = row.get("Institution Website", "")
            domain = row.get("Institution Domain", "")
            if website and domain and not row.get("Library URL"):
                library_url, library_source = discover_library_url(website, domain)
                row["Library URL"] = library_url
                row["Library URL Source"] = library_source
            if row.get("Library URL") and not row.get("Library Directory URL"):
                directory_url, directory_source = discover_directory_url(row["Library URL"])
                row["Library Directory URL"] = directory_url
                row["Library Directory Source"] = directory_source
        except Exception as exc:
            notes = row.get("Notes", "")
            suffix = f" | enrichment error: {type(exc).__name__}"
            if suffix not in notes:
                row["Notes"] = f"{notes}{suffix}".strip()
        if args.save_every > 0 and index % args.save_every == 0:
            write_rows(args.output, rows, fieldnames)
            print(f"Saved progress after {index} institutions")
        time.sleep(args.delay)

    write_rows(args.output, rows, fieldnames)
    print(f"Enriched {len(rows_to_process)} institutions into {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
