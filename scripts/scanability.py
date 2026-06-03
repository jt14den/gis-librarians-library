#!/usr/bin/env python3
"""
scanability.py -- Score HTML report pages for scanability heuristics.

Usage:
  python3 scripts/scanability.py docs/index.html [docs/directory.html ...]

Metrics scored:
  - Flesch Reading Ease (readability)
  - Heading density (words between headings)
  - Paragraph length (avg and max)
  - List usage ratio (list items vs paragraphs)
  - Bold density (bold phrases per 1,000 words)
  - Long paragraph count (>100 words)

No external dependencies. Python 3.8+.
"""

import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# HTML extraction
# ---------------------------------------------------------------------------

@dataclass
class Block:
    kind: str  # heading | paragraph | list_item | bold_phrase | callout_para
    level: Optional[int]  # heading level 1-6; None for others
    text: str
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.text.split())


class ReportParser(HTMLParser):
    """Extract semantic blocks from Quarto HTML output."""

    SKIP_TAGS = {"script", "style", "code", "pre", "nav", "footer",
                 "header", "button", "input", "select", "textarea"}
    HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}

    def __init__(self):
        super().__init__()
        self.blocks: list[Block] = []
        self._stack: list[str] = []
        self._buf: list[str] = []
        self._in_skip = 0
        self._in_heading: Optional[int] = None
        self._in_paragraph = False
        self._in_list_item = False
        self._in_bold = False
        self._bold_buf: list[str] = []
        self._callout_depth = 0

    def _flush(self, kind: str, level: Optional[int] = None):
        text = " ".join(" ".join(self._buf).split())
        self._buf = []
        if text.strip() and len(text.split()) >= 3:
            self.blocks.append(Block(kind=kind, level=level, text=text))

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        classes = (attr_dict.get("class") or "").split()

        if tag in self.SKIP_TAGS:
            self._in_skip += 1
            return
        if self._in_skip:
            return

        self._stack.append(tag)

        if tag in self.HEADING_TAGS:
            self._in_heading = self.HEADING_TAGS[tag]
            self._buf = []
        elif tag == "p":
            self._in_paragraph = True
            self._buf = []
        elif tag == "li":
            self._in_list_item = True
            self._buf = []
        elif tag in ("strong", "b"):
            self._in_bold = True
            self._bold_buf = []
        elif tag == "div":
            if any(c.startswith("callout") for c in classes):
                self._callout_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._in_skip = max(0, self._in_skip - 1)
            return
        if self._in_skip:
            return

        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

        if tag in self.HEADING_TAGS and self._in_heading is not None:
            self._flush("heading", level=self._in_heading)
            self._in_heading = None
        elif tag == "p":
            kind = "callout_para" if self._callout_depth > 0 else "paragraph"
            self._flush(kind)
            self._in_paragraph = False
        elif tag == "li":
            self._flush("list_item")
            self._in_list_item = False
        elif tag in ("strong", "b"):
            text = " ".join(self._bold_buf).strip()
            if text:
                self.blocks.append(Block(kind="bold_phrase", level=None, text=text))
            self._in_bold = False
            self._bold_buf = []
        elif tag == "div":
            if self._callout_depth > 0:
                self._callout_depth -= 1

    def handle_data(self, data):
        if self._in_skip:
            return
        if self._in_bold:
            self._bold_buf.append(data)
        active = (
            self._in_heading is not None
            or self._in_list_item
            or self._in_paragraph
        )
        if active:
            self._buf.append(data)


# ---------------------------------------------------------------------------
# Readability
# ---------------------------------------------------------------------------

def _count_syllables(word: str) -> int:
    """Approximate syllable count via vowel-cluster heuristic."""
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_reading_ease(text: str) -> float:
    """Flesch Reading Ease (0-100; higher = easier to read)."""
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    n_sentences = max(1, len(sentences))
    words = text.split()
    n_words = max(1, len(words))
    n_syllables = sum(_count_syllables(w) for w in words)
    return 206.835 - 1.015 * (n_words / n_sentences) - 84.6 * (n_syllables / n_words)


def _grade_flesch(score: float) -> str:
    if score >= 70:
        return "Easy"
    elif score >= 60:
        return "Standard"
    elif score >= 50:
        return "Fairly Difficult"
    elif score >= 30:
        return "Difficult"
    else:
        return "Very Difficult"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@dataclass
class ScanabilityReport:
    file: str
    total_words: int
    flesch_score: float
    n_headings: int
    avg_words_between_headings: int
    max_words_between_headings: int
    n_paragraphs: int
    avg_para_words: float
    max_para_words: int
    long_para_count: int       # paragraphs > 100 words
    very_long_para_count: int  # paragraphs > 150 words
    n_list_items: int
    list_ratio: float
    n_bold_phrases: int
    bold_per_1000_words: float
    n_callout_paras: int
    flags: list[str] = field(default_factory=list)
    long_paragraphs: list[tuple[int, str]] = field(default_factory=list)  # (words, preview)


def analyze(path: Path) -> ScanabilityReport:
    html = path.read_text(encoding="utf-8", errors="replace")
    parser = ReportParser()
    parser.feed(html)
    blocks = parser.blocks

    body_kinds = {"paragraph", "list_item", "callout_para"}
    body_blocks = [b for b in blocks if b.kind in body_kinds]
    all_text = " ".join(b.text for b in body_blocks)
    total_words = len(all_text.split())

    flesch = flesch_reading_ease(all_text)

    headings = [b for b in blocks if b.kind == "heading"]
    n_headings = len(headings)

    # Words between consecutive headings
    words_between: list[int] = []
    current_words = 0
    for b in blocks:
        if b.kind == "heading":
            if current_words > 0:
                words_between.append(current_words)
            current_words = 0
        elif b.kind in body_kinds:
            current_words += b.word_count
    if current_words > 0:
        words_between.append(current_words)

    avg_between = int(sum(words_between) / max(1, len(words_between)))
    max_between = max(words_between) if words_between else 0

    paras = [b for b in blocks if b.kind == "paragraph"]
    n_paras = len(paras)
    para_words = [b.word_count for b in paras]
    avg_para = round(sum(para_words) / max(1, n_paras), 1)
    max_para = max(para_words) if para_words else 0
    long_paras = [(b.word_count, b.text[:80] + "...") for b in paras if b.word_count > 100]
    very_long_paras = [b for b in paras if b.word_count > 150]

    list_items = [b for b in blocks if b.kind == "list_item"]
    n_list = len(list_items)
    list_ratio = round(n_list / max(1, n_paras + n_list), 2)

    bold_phrases = [b for b in blocks if b.kind == "bold_phrase"]
    n_bold = len(bold_phrases)
    bold_per_1k = round((n_bold / max(1, total_words)) * 1000, 1)

    callout_paras = [b for b in blocks if b.kind == "callout_para"]

    r = ScanabilityReport(
        file=path.name,
        total_words=total_words,
        flesch_score=round(flesch, 1),
        n_headings=n_headings,
        avg_words_between_headings=avg_between,
        max_words_between_headings=max_between,
        n_paragraphs=n_paras,
        avg_para_words=avg_para,
        max_para_words=max_para,
        long_para_count=len(long_paras),
        very_long_para_count=len(very_long_paras),
        n_list_items=n_list,
        list_ratio=list_ratio,
        n_bold_phrases=n_bold,
        bold_per_1000_words=bold_per_1k,
        n_callout_paras=len(callout_paras),
        long_paragraphs=long_paras,
    )

    # Flags
    if avg_between > 200:
        r.flags.append(
            f"Heading density: avg {avg_between} words between headings (target <200)"
        )
    if avg_para > 75:
        r.flags.append(
            f"Paragraph length: avg {avg_para:.0f} words/paragraph (target <75)"
        )
    if max_para > 150:
        r.flags.append(
            f"Longest paragraph: {max_para} words (target <150)"
        )
    if len(long_paras) > 0:
        r.flags.append(
            f"{len(long_paras)} paragraph(s) exceed 100 words"
        )
    if list_ratio < 0.15:
        r.flags.append(
            f"Low list usage: {list_ratio:.0%} of content blocks are lists (target >15%)"
        )
    if bold_per_1k < 1.0 and total_words > 500:
        r.flags.append(
            f"Low bold density: {bold_per_1k} bold phrases/1,000 words (target >1)"
        )
    if flesch < 40:
        r.flags.append(
            f"Low readability: Flesch {flesch:.0f} -- {_grade_flesch(flesch)}"
        )

    return r


def print_report(r: ScanabilityReport, verbose: bool = False):
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  {r.file}")
    print(sep)

    def row(label, value, note=""):
        note_str = f"  ({note})" if note else ""
        print(f"  {label:<34} {value}{note_str}")

    print()
    row("Total words", f"{r.total_words:,}")
    row("Flesch Reading Ease", f"{r.flesch_score}", _grade_flesch(r.flesch_score))
    print()
    row("Headings", r.n_headings)
    row("Avg words between headings", r.avg_words_between_headings)
    row("Max words between headings", r.max_words_between_headings)
    print()
    row("Paragraphs", r.n_paragraphs)
    row("Avg words/paragraph", r.avg_para_words)
    row("Max words/paragraph", r.max_para_words)
    row("Paragraphs >100 words", r.long_para_count)
    row("Paragraphs >150 words", r.very_long_para_count)
    print()
    row("List items", r.n_list_items)
    row("List ratio", f"{r.list_ratio:.0%}", "list items / (paras + list items)")
    print()
    row("Bold phrases", r.n_bold_phrases)
    row("Bold phrases/1,000 words", r.bold_per_1000_words)
    row("Callout paragraphs", r.n_callout_paras)
    print()

    if r.flags:
        print("  FLAGS:")
        for f in r.flags:
            print(f"    * {f}")
    else:
        print("  No flags raised.")

    if verbose and r.long_paragraphs:
        print(f"\n  Long paragraphs (>100 words):")
        for words, preview in r.long_paragraphs:
            print(f"    [{words}w] {preview}")

    print()


def main():
    args = sys.argv[1:]
    verbose = "--verbose" in args or "-v" in args
    paths = [a for a in args if not a.startswith("-")]

    if not paths:
        print("Usage: python3 scripts/scanability.py [-v] docs/index.html [...]")
        print("  -v  show previews of long paragraphs")
        sys.exit(1)

    for arg in paths:
        path = Path(arg)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            continue
        report = analyze(path)
        print_report(report, verbose=verbose)


if __name__ == "__main__":
    main()
