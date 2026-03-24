#!/usr/bin/env python3
"""Collect raw GIS librarian candidates from library staff and guide pages."""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

KEYWORDS = (
    "gis librarian",
    "geospatial librarian",
    "geospatial data librarian",
    "map librarian",
    "maps librarian",
    "gis specialist",
    "geospatial",
    "spatial data",
    "map library",
    "maps and data",
)

COMMON_PATHS = (
    "",
    "/about/staff",
    "/about/directory",
    "/staff",
    "/directory",
    "/people",
    "/research-help/subject-librarians",
    "/services/data-gis",
    "/services/maps-geospatial-data",
    "/services/gis",
    "/guides/gis",
    "/guides/maps",
)
DISCOVERY_HINTS = (
    "staff",
    "directory",
    "people",
    "subject",
    "liaison",
    "research help",
    "gis",
    "geo",
    "map",
    "maps",
    "data",
    "services",
)
GIS_HINTS = ("gis", "geo", "geospatial", "map", "maps", "spatial", "data")
MAX_DISCOVERED_LINKS = 8
PERSON_PAGE_HINTS = ("staff", "directory", "people", "profile", "bio", "subject", "liaison")
ROLE_HINTS = (
    "librarian",
    "specialist",
    "coordinator",
    "director",
    "head",
    "manager",
    "analyst",
    "services",
    "research support",
    "data services",
    "maps, imagery",
)
NOISY_URL_HINTS = (
    "/az/databases",
    "/databases",
    "/database",
    "/map/interactive",
    "/news/",
    "/events/",
    "/locations-maps",
    "publications.ebsco.com",
    "openathens",
    "ebsco",
    "browzine",
    "mapsengine.google.com",
)
BAD_NAME_WORDS = {
    "email",
    "services",
    "service",
    "search",
    "keyword",
    "title",
    "author",
    "full",
    "text",
    "phone",
    "campus",
    "public",
    "library",
    "libraries",
    "subject",
    "research",
    "help",
    "news",
    "upcoming",
    "hours",
    "locations",
    "account",
    "west",
    "valley",
    "tempe",
    "polytechnic",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
WHITESPACE_RE = re.compile(r"\s+")
NAME_RE = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z.'-]+){1,3})\b")


class LinkTextParser(HTMLParser):
    """Extract visible text and links from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.text_chunks: list[str] = []
        self._current_href: str | None = None
        self._current_link_text: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if tag == "a":
            self._current_href = attrs_dict.get("href")
            self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "a" and self._current_href:
            label = normalize_space(" ".join(self._current_link_text))
            self.links.append((self._current_href, label))
            self._current_href = None
            self._current_link_text = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = normalize_space(html.unescape(data))
        if not cleaned:
            return
        self.text_chunks.append(cleaned)
        if self._current_href is not None:
            self._current_link_text.append(cleaned)


@dataclass
class Candidate:
    institution: str
    institution_domain: str
    source_url: str
    matched_keyword: str
    matched_excerpt: str
    candidate_name: str
    candidate_title: str
    candidate_email: str
    candidate_profile_url: str


def normalize_space(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def fetch_url(url: str, user_agent: str, timeout: int) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        return content_type, body


def iter_candidate_urls(base_url: str, explicit_directory_url: str) -> Iterable[str]:
    seen: set[str] = set()
    for url in (explicit_directory_url,):
        if url and url not in seen:
            seen.add(url)
            yield url
    for path in COMMON_PATHS:
        url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        if url not in seen:
            seen.add(url)
            yield url


def split_sentences(text: str) -> list[str]:
    return [normalize_space(chunk) for chunk in re.split(r"(?<=[.!?])\s+", text) if normalize_space(chunk)]


def excerpt_around_keyword(text: str, keyword: str, radius: int = 180) -> str:
    lower = text.lower()
    idx = lower.find(keyword.lower())
    if idx == -1:
        return text[: radius * 2]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(keyword) + radius)
    return normalize_space(text[start:end])


def first_name_candidate(text: str) -> str:
    for match in NAME_RE.finditer(text):
        candidate = match.group(1).strip()
        parts = [part.strip(".,").lower() for part in candidate.split()]
        if any(part in BAD_NAME_WORDS for part in parts):
            continue
        return candidate
    return ""


def guess_title(text: str) -> str:
    lower = text.lower()
    for keyword in KEYWORDS:
        if keyword in lower:
            return keyword.title()
    return ""


def choose_profile_match(source_url: str, links: list[tuple[str, str]], sentence: str) -> tuple[str, str]:
    sentence_lower = sentence.lower()
    for href, label in links:
        if not href:
            continue
        candidate = f"{label} {href}".lower()
        if any(token in candidate for token in ("profile", "staff", "directory", "people", "bio")):
            if label and label.lower() in sentence_lower:
                return urljoin(source_url, href), label
    for href, label in links:
        if label and label.lower() in sentence_lower:
            return urljoin(source_url, href), label
    return "", ""


def is_noisy_url(url: str) -> bool:
    lower = url.lower()
    return any(token in lower for token in NOISY_URL_HINTS)


def looks_like_person_page(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(token in path for token in PERSON_PAGE_HINTS)


def has_role_signal(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ROLE_HINTS)


def is_plausible_candidate(
    source_url: str,
    sentence: str,
    candidate_name: str,
    candidate_email: str,
    candidate_profile_url: str,
) -> bool:
    if is_noisy_url(source_url):
        return False
    if candidate_profile_url and is_noisy_url(candidate_profile_url):
        return False
    page_is_person_like = looks_like_person_page(source_url)
    sentence_has_role = has_role_signal(sentence)
    has_name = bool(candidate_name)
    has_email = bool(candidate_email)
    has_profile = bool(candidate_profile_url)
    return sentence_has_role and (
        (page_is_person_like and (has_name or has_profile))
        or (has_profile and has_name)
        or (page_is_person_like and has_email and has_name)
    )


def discover_urls(source_url: str, html_body: str, institution_domain: str) -> list[str]:
    parser = LinkTextParser()
    parser.feed(html_body)
    discovered: list[str] = []
    seen: set[str] = set()

    for href, label in parser.links:
        if not href:
            continue
        absolute = urljoin(source_url, href)
        if is_noisy_url(absolute):
            continue
        if institution_domain and institution_domain not in absolute:
            continue
        combined = f"{label} {absolute}".lower()
        parsed = urlparse(absolute)
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        is_libguides = "libguides" in host
        has_discovery_hint = any(hint in combined for hint in DISCOVERY_HINTS)
        has_gis_hint = any(hint in combined for hint in GIS_HINTS)
        has_directory_path = any(token in path for token in ("/staff", "/directory", "/people", "/subject", "/liaison"))
        has_service_path = any(token in path for token in ("/gis", "/geospatial", "/maps", "/data"))
        if is_libguides and not has_gis_hint:
            continue
        if has_discovery_hint or has_directory_path or has_service_path:
            if absolute not in seen:
                seen.add(absolute)
                discovered.append(absolute)
        if len(discovered) >= MAX_DISCOVERED_LINKS:
            break

    return discovered


def extract_candidates(
    institution: str,
    institution_domain: str,
    source_url: str,
    html_body: str,
) -> list[Candidate]:
    parser = LinkTextParser()
    parser.feed(html_body)
    sentences = split_sentences(" ".join(parser.text_chunks))
    candidates: list[Candidate] = []

    for sentence in sentences:
        lower = sentence.lower()
        matched = next((keyword for keyword in KEYWORDS if keyword in lower), None)
        if not matched:
            continue
        snippet = excerpt_around_keyword(sentence, matched)
        candidate_name = first_name_candidate(snippet)
        candidate_email = "; ".join(sorted(set(EMAIL_RE.findall(snippet))))
        candidate_profile_url, candidate_profile_label = choose_profile_match(source_url, parser.links, snippet)
        profile_name = first_name_candidate(candidate_profile_label)
        if profile_name:
            candidate_name = profile_name
        if not is_plausible_candidate(
            source_url,
            snippet,
            candidate_name,
            candidate_email,
            candidate_profile_url,
        ):
            continue
        candidates.append(
            Candidate(
                institution=institution,
                institution_domain=institution_domain,
                source_url=source_url,
                matched_keyword=matched,
                matched_excerpt=snippet[:500],
                candidate_name=candidate_name,
                candidate_title=guess_title(sentence),
                candidate_email=candidate_email,
                candidate_profile_url=candidate_profile_url,
            )
        )

    return dedupe_candidates(candidates)


def dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    deduped: list[Candidate] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        key = (
            candidate.source_url,
            candidate.candidate_name.lower(),
            candidate.matched_excerpt.lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def read_institutions(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institutions", required=True, type=Path, help="CSV input of institutions")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for collector output")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--save-every", type=int, default=10, help="Save output every N institutions")
    parser.add_argument(
        "--user-agent",
        default="GISLibrarianCollector/0.1 (+https://example.org/contact)",
        help="User-Agent for HTTP requests",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    institutions = read_institutions(args.institutions)
    candidate_rows: list[dict[str, str]] = []
    fetch_log_rows: list[dict[str, str]] = []

    for index, row in enumerate(institutions, start=1):
        institution = row.get("Institution", "").strip()
        domain = row.get("Institution Domain", "").strip()
        base_url = row.get("Library URL", "").strip()
        directory_url = row.get("Library Directory URL", "").strip()
        if not institution or not base_url:
            fetch_log_rows.append(
                {
                    "institution": institution,
                    "url": base_url or directory_url,
                    "status": "skipped",
                    "detail": "missing Institution or Library URL",
                }
            )
            continue

        queued_urls = list(iter_candidate_urls(base_url, directory_url))
        seen_urls: set[str] = set()

        while queued_urls:
            candidate_url = queued_urls.pop(0)
            if candidate_url in seen_urls:
                continue
            seen_urls.add(candidate_url)
            try:
                content_type, body = fetch_url(candidate_url, args.user_agent, args.timeout)
                if "html" not in content_type.lower():
                    fetch_log_rows.append(
                        {
                            "institution": institution,
                            "url": candidate_url,
                            "status": "skipped",
                            "detail": f"non-html content-type: {content_type}",
                        }
                    )
                    continue
                found = extract_candidates(institution, domain, candidate_url, body)
                if candidate_url == base_url:
                    for discovered_url in discover_urls(candidate_url, body, domain):
                        if discovered_url not in seen_urls and discovered_url not in queued_urls:
                            queued_urls.append(discovered_url)
                for candidate in found:
                    candidate_rows.append(candidate.__dict__)
                fetch_log_rows.append(
                    {
                        "institution": institution,
                        "url": candidate_url,
                        "status": "ok",
                        "detail": f"{len(found)} candidates",
                    }
                )
            except HTTPError as exc:
                fetch_log_rows.append(
                    {
                        "institution": institution,
                        "url": candidate_url,
                        "status": "http_error",
                        "detail": f"{exc.code} {exc.reason}",
                    }
                )
            except URLError as exc:
                fetch_log_rows.append(
                    {
                        "institution": institution,
                        "url": candidate_url,
                        "status": "url_error",
                        "detail": str(exc.reason),
                    }
                )
            except Exception as exc:  # pragma: no cover
                fetch_log_rows.append(
                    {
                        "institution": institution,
                        "url": candidate_url,
                        "status": "error",
                        "detail": str(exc),
                    }
                )
            time.sleep(args.delay)
        if args.save_every > 0 and index % args.save_every == 0:
            write_csv(
                args.output_dir / "raw_candidates.csv",
                candidate_rows,
                [
                    "institution",
                    "institution_domain",
                    "source_url",
                    "matched_keyword",
                    "matched_excerpt",
                    "candidate_name",
                    "candidate_title",
                    "candidate_email",
                    "candidate_profile_url",
                ],
            )
            write_csv(
                args.output_dir / "fetch_log.csv",
                fetch_log_rows,
                ["institution", "url", "status", "detail"],
            )
            print(f"Saved progress after {index} institutions")

    write_csv(
        args.output_dir / "raw_candidates.csv",
        candidate_rows,
        [
            "institution",
            "institution_domain",
            "source_url",
            "matched_keyword",
            "matched_excerpt",
            "candidate_name",
            "candidate_title",
            "candidate_email",
            "candidate_profile_url",
        ],
    )
    write_csv(
        args.output_dir / "fetch_log.csv",
        fetch_log_rows,
        ["institution", "url", "status", "detail"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
