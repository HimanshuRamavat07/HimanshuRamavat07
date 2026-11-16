#!/usr/bin/env python3
"""Wrap raw report body HTML with SEO, accessibility, and shared stylesheet."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from extract_stories import extract_report, validate_new_report
from site_shell import asset_script, automation_modal, font_links, search_overlay, site_footer, site_nav

PAGES_BASE = "https://aidaily.is-a.bot"
META_DESC_PATTERN = re.compile(
    r'<meta\s+name="description"\s+content="([^"]*)"\s*/?>',
    re.IGNORECASE,
)

STAR_PATTERN = re.compile(r'(<span class="stars">Impact:\s*)([⭐]+)(</span>)')
EXTERNAL_LINK_PATTERN = re.compile(
    r'<a\s+([^>]*?)href="(https?://[^"]+)"([^>]*)>',
    re.IGNORECASE,
)
HEADING_OPEN_RE = re.compile(
    r"<(h[23])(\s[^>]*)?>",
    re.IGNORECASE,
)
ID_ATTR_RE = re.compile(r'\bid=(["\'])(.*?)\1', re.IGNORECASE)
TAG_NAME_RE = re.compile(r"^h[23]$", re.IGNORECASE)


def format_display_date(date: datetime) -> str:
    return date.strftime("%B %d, %Y")


def format_iso_date(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


def format_short_date(date: datetime) -> str:
    return date.strftime("%b %d, %Y")


def fix_stars(content: str) -> str:
    def repl(match: re.Match[str]) -> str:
        count = match.group(2).count("⭐")
        return (
            f"{match.group(1)}"
            f'<span aria-hidden="true">{match.group(2)}</span>'
            f'<span class="visually-hidden">Impact: {count} out of 5</span>'
            f"{match.group(3)}"
        )

    return STAR_PATTERN.sub(repl, content)


def fix_external_links(content: str) -> str:
    def repl(match: re.Match[str]) -> str:
        before, href, after = match.group(1), match.group(2), match.group(3)
        combined = before + after
        if "target=" in combined:
            return match.group(0)
        return f'<a {before}href="{href}"{after} target="_blank" rel="noopener noreferrer">'

    return EXTERNAL_LINK_PATTERN.sub(repl, content)


def fix_research_headings(content: str) -> str:
    marker = '<h2 id="research">📚 Research Worth Reading</h2>'
    if marker not in content:
        marker = "<h2>📚 Research Worth Reading</h2>"
    if marker not in content:
        return content
    before, after = content.split(marker, 1)
    next_h2 = after.find("<h2")
    if next_h2 == -1:
        research_block = after
        rest = ""
    else:
        research_block = after[:next_h2]
        rest = after[next_h2:]
    research_block = research_block.replace("<h4>", "<h3>").replace("</h4>", "</h3>")
    return before + marker + research_block + rest


def extract_body(raw_html: str) -> str:
    if "<body" in raw_html.lower():
        match = re.search(r"<body[^>]*>(.*)</body>", raw_html, re.DOTALL | re.IGNORECASE)
        if match:
            inner = match.group(1).strip()
            container_match = re.search(
                r'<div class="container">(.*)</div>\s*$',
                inner,
                re.DOTALL | re.IGNORECASE,
            )
            if container_match:
                return container_match.group(1).strip()
            return inner
    return raw_html.strip()


def build_toc(has_new_watch_heading: bool = True) -> str:
    """Legacy fixed TOC kept for callers; prefer build_toc_from_body."""
    watch_label = "What to Watch Next" if has_new_watch_heading else "What I Would Watch Next"
    sections = [
        ("top-developments", "Top Developments"),
        ("emerging-trends", "Emerging AI Trends"),
        ("developer-coding", "Developer & Coding AI"),
        ("agentic-watch", "Agentic AI Watch"),
        ("security-watch", "AI Security Watch"),
        ("research", "Research Worth Reading"),
        ("watch-next", watch_label),
        ("bottom-line", "Bottom Line"),
    ]
    items = "\n".join(f'        <li><a href="#{sid}">{label}</a></li>' for sid, label in sections)
    return f"""
    <nav class="toc" aria-label="Table of contents">
      <h2>On this page</h2>
      <ul>
{items}
      </ul>
    </nav>"""


def add_section_ids(content: str) -> str:
    replacements = [
        (r"<h2>🔥 Top Developments</h2>", '<h2 id="top-developments">🔥 Top Developments</h2>'),
        (r"<h2>🧠 Emerging AI Trends</h2>", '<h2 id="emerging-trends">🧠 Emerging AI Trends</h2>'),
        (r"<h2>💻 Developer & Coding AI</h2>", '<h2 id="developer-coding">💻 Developer & Coding AI</h2>'),
        (r"<h2>🧩 Agentic AI Watch</h2>", '<h2 id="agentic-watch">🧩 Agentic AI Watch</h2>'),
        (r"<h2>🔐 AI Security Watch</h2>", '<h2 id="security-watch">🔐 AI Security Watch</h2>'),
        (r"<h2>📚 Research Worth Reading</h2>", '<h2 id="research">📚 Research Worth Reading</h2>'),
        (r"<h2>🚀 What to Watch Next</h2>", '<h2 id="watch-next">🚀 What to Watch Next</h2>'),
        (r"<h2>🚀 What I Would Watch Next</h2>", '<h2 id="watch-next">🚀 What I Would Watch Next</h2>'),
        (r'<div class="bottom-line">', '<div class="bottom-line" id="bottom-line">'),
    ]
    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content, count=1)
    return content


def strip_wrapped_chrome(content: str) -> str:
    content_match = re.search(
        r'<main class="report-content">(.*)</main>',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if content_match:
        body = content_match.group(1).strip()
        body = re.sub(r'<p class="signature">.*?</p>\s*', "", body, count=1, flags=re.DOTALL)
        return body.strip()

    body = content
    body = re.sub(r'<div class="read-progress">.*?</div>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<header class="site-nav">.*?</header>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<p class="report-back">.*?</p>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<header class="report-article-header">.*?</header>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r"<header class=\"report-header\">.*?</header>\s*", "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<div class="report-layout">.*?</div>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r"<p class=\"intro\">.*?</p>\s*", "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<p class="meta"><a href="\.\./index\.html">.*?</a></p>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r"<h1>🤖 AI Daily Intelligence —.*?</h1>\s*", "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<nav class="toc".*?</nav>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<p class="signature">.*?</p>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<footer class="site-footer">.*', "", body, count=1, flags=re.DOTALL)
    return body.strip()


def looks_like_new_report(content: str) -> bool:
    return "data-story" in content or "data-report-date" in content


def slugify_heading(text: str) -> str:
    cleaned = re.sub(r"[\U0001f300-\U0001faff\U00002702-\U000027b0\U0001f900-\U0001f9ff]+", "", text)
    cleaned = _norm_space(cleaned)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", cleaned.lower()).strip("-")
    return slug or "section"


def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _inside_bottom_line(content: str, index: int) -> bool:
    last_open = content.rfind('<div class="bottom-line"', 0, index)
    if last_open == -1:
        return False
    last_close = content.rfind("</div>", 0, index)
    return last_close < last_open


def ensure_unique_heading_ids(content: str) -> str:
    """Ensure h2/h3 (and bottom-line) ids exist and are unique within the fragment."""
    used: dict[str, int] = {}

    def unique_id(base: str) -> str:
        if base not in used:
            used[base] = 1
            return base
        used[base] += 1
        candidate = f"{base}-{used[base]}"
        while candidate in used:
            used[base] += 1
            candidate = f"{base}-{used[base]}"
        used[candidate] = 1
        return candidate

    # bottom-line div without id
    if re.search(r'<div class="bottom-line"(?![^>]*\bid=)', content):
        content = re.sub(
            r'<div class="bottom-line"',
            f'<div class="bottom-line" id="{unique_id("bottom-line")}"',
            content,
            count=1,
        )
    else:
        match = re.search(r'<div class="bottom-line"[^>]*\bid=(["\'])(.*?)\1', content)
        if match:
            used[match.group(2)] = 1

    parts: list[str] = []
    pos = 0
    for match in HEADING_OPEN_RE.finditer(content):
        parts.append(content[pos : match.start()])
        tag = match.group(1)
        attrs = match.group(2) or ""
        # Headings inside .bottom-line keep the div's #bottom-line anchor
        if _inside_bottom_line(content, match.start()):
            parts.append(match.group(0))
            pos = match.end()
            continue
        end = content.find(f"</{tag}>", match.end())
        if end == -1:
            end = content.find(f"</{tag.lower()}>", match.end())
        inner = content[match.end() : end] if end != -1 else ""
        text = _norm_space(re.sub(r"<[^>]+>", "", inner))
        id_match = ID_ATTR_RE.search(attrs)
        if id_match:
            base = id_match.group(2)
            new_id = unique_id(base)
            attrs = ID_ATTR_RE.sub(f'id="{html.escape(new_id, quote=True)}"', attrs, count=1)
        else:
            new_id = unique_id(slugify_heading(text))
            attrs = f'{attrs} id="{html.escape(new_id, quote=True)}"'
        parts.append(f"<{tag}{attrs}>")
        pos = match.end()
    parts.append(content[pos:])
    return "".join(parts)


class _TocParser(HTMLParser):
    """Collect h2/h3 inside report body, excluding nav/footer/related/summary-deck."""

    SKIP_ATTRS = {
        "data-summary-deck",
        "data-related-reports",
    }
    SKIP_CLASSES = {
        "summary-deck",
        "related-reports",
        "site-nav",
        "site-footer",
        "toc",
    }
    SKIP_TAGS = {"nav", "footer", "header"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[tuple[str, str]] = []
        self._skip_depth = 0
        self._capture: str | None = None
        self._chunks: list[str] = []
        self._current_id = ""
        self._stack: list[tuple[str, bool]] = []  # tag, is_skip_root
        self._bottom_line_depth = 0
        self._bottom_line_id = ""
        self._bottom_line_label_chunks: list[str] = []
        self._capture_bottom_label = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        classes = set((ad.get("class") or "").split())
        skip_here = False
        if self._skip_depth == 0:
            if tag in self.SKIP_TAGS:
                skip_here = True
            if any(a in ad for a in self.SKIP_ATTRS):
                skip_here = True
            if classes & self.SKIP_CLASSES:
                skip_here = True
            if tag == "aside" and "summary-deck" in classes:
                skip_here = True
            if tag == "section" and ad.get("data-related-reports") is not None:
                skip_here = True
        if self._skip_depth > 0 or skip_here:
            self._skip_depth += 1
            self._stack.append((tag, True))
            return

        if tag == "div" and "bottom-line" in classes:
            self._bottom_line_depth = 1
            self._bottom_line_id = ad.get("id") or "bottom-line"
            self._bottom_line_label_chunks = []
            self._stack.append((tag, False))
            return

        if self._bottom_line_depth > 0:
            if tag == "div":
                self._bottom_line_depth += 1
            if tag in ("h2", "h3") and not self._bottom_line_label_chunks:
                self._capture_bottom_label = True
            self._stack.append((tag, False))
            return

        self._stack.append((tag, False))
        if tag in ("h2", "h3") and self._skip_depth == 0:
            self._capture = tag
            self._chunks = []
            self._current_id = ad.get("id") or ""

    def handle_endtag(self, tag: str) -> None:
        if self._capture_bottom_label and tag in ("h2", "h3"):
            self._capture_bottom_label = False

        if self._bottom_line_depth > 0 and tag == "div":
            self._bottom_line_depth -= 1
            if self._bottom_line_depth == 0:
                label = _norm_space("".join(self._bottom_line_label_chunks)) or "Bottom Line"
                label = re.sub(
                    r"^[\U0001f300-\U0001faff\U00002702-\U000027b0\U0001f900-\U0001f9ff]+\s*",
                    "",
                    label,
                )
                self.entries.append((self._bottom_line_id or "bottom-line", label or "Bottom Line"))
                self._bottom_line_id = ""
                self._bottom_line_label_chunks = []

        if self._capture and tag == self._capture and self._skip_depth == 0 and self._bottom_line_depth == 0:
            label = _norm_space("".join(self._chunks))
            label = re.sub(
                r"^[\U0001f300-\U0001faff\U00002702-\U000027b0\U0001f900-\U0001f9ff]+\s*",
                "",
                label,
            )
            if label and label.lower() != "on this page":
                hid = self._current_id or slugify_heading(label)
                self.entries.append((hid, label))
            self._capture = None
            self._chunks = []

        if self._stack:
            _t, was_skip = self._stack.pop()
            if was_skip and self._skip_depth > 0:
                self._skip_depth -= 1
        elif self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_bottom_label:
            self._bottom_line_label_chunks.append(data)
        elif self._capture and self._skip_depth == 0 and self._bottom_line_depth == 0:
            self._chunks.append(data)


def collect_toc_entries(body_html: str) -> list[tuple[str, str]]:
    parser = _TocParser()
    parser.feed(body_html or "")
    parser.close()
    return parser.entries


def build_toc_from_body(body_html: str) -> str:
    entries = collect_toc_entries(body_html)
    if not entries:
        return build_toc(has_new_watch_heading=True)
    items = "\n".join(
        f'        <li><a href="#{html.escape(sid)}">{html.escape(label)}</a></li>'
        for sid, label in entries
    )
    return f"""
    <nav class="toc" aria-label="Table of contents">
      <h2>On this page</h2>
      <ul>
{items}
      </ul>
    </nav>"""


def filter_summary_deck_slots(content: str) -> str:
    """Remove empty data-summary sections; drop the deck entirely if none remain."""

    def section_has_content(inner: str) -> bool:
        text = _norm_space(re.sub(r"<[^>]+>", " ", inner))
        # Strip the section's own heading text-ish: if only whitespace/empty tags, drop
        return bool(text)

    def repl_aside(match: re.Match[str]) -> str:
        aside = match.group(0)
        kept: list[str] = []
        for sec in re.finditer(
            r'(<section\b[^>]*data-summary=(["\'])(.*?)\2[^>]*>)(.*?)(</section>)',
            aside,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            inner = sec.group(4)
            # Content besides the heading
            without_heading = re.sub(
                r"<h[1-6][^>]*>.*?</h[1-6]>",
                "",
                inner,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if section_has_content(without_heading):
                kept.append(sec.group(0))
        if not kept:
            return ""
        open_tag = re.match(r"<aside\b[^>]*>", aside, flags=re.IGNORECASE)
        open_s = open_tag.group(0) if open_tag else '<aside class="summary-deck" data-summary-deck>'
        return f"{open_s}\n" + "\n".join(kept) + "\n</aside>"

    return re.sub(
        r"<aside\b[^>]*(?:summary-deck|data-summary-deck)[^>]*>.*?</aside>",
        repl_aside,
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )


def inject_report_article_meta(body: str, date: datetime, title: str, reading_minutes: int | None) -> str:
    iso = format_iso_date(date)
    minutes = reading_minutes if reading_minutes and reading_minutes > 0 else 10
    safe_title = html.escape(title, quote=True)

    if re.search(r"<article\b[^>]*class=\"[^\"]*\breport\b", body, re.IGNORECASE):
        def enrich(match: re.Match[str]) -> str:
            tag = match.group(0)
            if "data-report-date=" not in tag:
                tag = tag[:-1] + f' data-report-date="{iso}">'
            if "data-report-title=" not in tag:
                tag = tag[:-1] + f' data-report-title="{safe_title}">'
            if "data-reading-minutes=" not in tag:
                tag = tag[:-1] + f' data-reading-minutes="{minutes}">'
            return tag

        body = re.sub(r"<article\b[^>]*>", enrich, body, count=1, flags=re.IGNORECASE)
        if "data-report-body" not in body and 'class="report-body"' not in body:
            body = re.sub(
                r"(<article\b[^>]*>)",
                r'\1\n<div class="report-body" data-report-body>',
                body,
                count=1,
                flags=re.IGNORECASE,
            )
            body = re.sub(r"</article>\s*$", "</div>\n</article>", body, count=1, flags=re.IGNORECASE)
        return body

    return (
        f'<article class="report" data-report-date="{iso}" '
        f'data-report-title="{safe_title}" data-reading-minutes="{minutes}">\n'
        f'<div class="report-body" data-report-body>\n{body}\n</div>\n</article>'
    )


def prepare_report_body(raw_html: str) -> str:
    body = extract_body(raw_html)
    body = strip_wrapped_chrome(raw_html if '<main class="report-content">' in raw_html else body)
    body = add_section_ids(body)
    body = fix_research_headings(body)
    body = fix_stars(body)
    body = fix_external_links(body)
    body = filter_summary_deck_slots(body)
    body = ensure_unique_heading_ids(body)
    return body


def build_report_page(date: datetime, description: str, body: str) -> str:
    display = format_display_date(date)
    short_date = format_short_date(date)
    iso = format_iso_date(date)
    title = f"AI Daily Intelligence — {display}"
    canonical = f"{PAGES_BASE}/reports/{iso}.html"
    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    intro = (
        "Daily briefing drafted by AI across models, agents, "
        "developer tools, research papers, and security."
    )

    extract = extract_report(body, strict=False)
    minutes = extract.reading_minutes
    body = inject_report_article_meta(body, date, title, minutes)
    toc = build_toc_from_body(body)

    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": title,
            "datePublished": iso,
            "author": {"@type": "Organization", "name": "AI Intelligence Automation"},
            "publisher": {"@type": "Organization", "name": "AI Daily Intelligence"},
            "description": description,
            "mainEntityOfPage": canonical,
        },
        indent=2,
    )

    related_block = """
    <section class="related-reports" data-related-reports>
      <h2>Related reports</h2>
      <p class="related-reports-note">Browse the <a href="../archive/index.html">archive</a> for earlier briefings.</p>
    </section>"""

    minutes_label = f"{minutes} min read" if minutes else "Daily brief"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <meta name="description" content="{safe_desc}">
  <link rel="canonical" href="{html.escape(canonical)}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{safe_title}">
  <meta property="og:description" content="{safe_desc}">
  <meta property="og:url" content="{html.escape(canonical)}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{safe_title}">
  <meta name="twitter:description" content="{safe_desc}">
{font_links()}
  <link rel="stylesheet" href="../assets/style.css">
  <script type="application/ld+json">
{json_ld}
  </script>
</head>
<body class="report-page">
<div class="read-progress" aria-hidden="true"><div class="read-progress-bar" id="read-progress"></div></div>
{site_nav(home_href="../index.html", archive_href="../archive/index.html", rss_href="../feed.xml", active="archive")}
<p class="report-back"><a href="../archive/index.html">← Back to archive</a></p>
<div class="container">
  <header class="report-article-header">
    <h1>🤖 AI Daily Intelligence — {display}</h1>
    <div class="report-meta-row">
      <span class="report-meta-item">{short_date}</span>
      <span class="report-meta-sep" aria-hidden="true">|</span>
      <span class="report-meta-chip">{html.escape(minutes_label)}</span>
    </div>
    <p class="intro">{intro}</p>
  </header>
  <div class="report-layout">
    <aside class="report-sidebar" aria-label="Section navigation">
      <details class="toc-mobile">
        <summary>On this page</summary>
{toc}
      </details>
      <div class="toc-desktop">
{toc}
      </div>
    </aside>
    <main class="report-content">
{body}
{related_block}
      <p class="signature">Drafted by AI from the sources linked above. Verify details before acting on them. · <a href="https://github.com/HimanshuRamavat07/HimanshuRamavat07" target="_blank" rel="noopener noreferrer">Source repository</a></p>
    </main>
  </div>
</div>
{site_footer()}
{automation_modal()}
{search_overlay(prefix="../")}
{asset_script("../", "theme.js")}
{asset_script("../", "modal.js")}
{asset_script("../", "search-data.js")}
{asset_script("../", "search.js")}
{asset_script("../", "report.js")}
</body>
</html>
"""


def validate_new_report_html(raw_html: str) -> list[str]:
    body = prepare_report_body(raw_html)
    extract = extract_report(body, strict=True)
    return validate_new_report(extract)


def wrap_report_to_path(
    *,
    report_date: datetime,
    description: str,
    source_html: str,
    output: Path,
    strict_new: bool | None = None,
) -> None:
    if strict_new is None:
        strict_new = looks_like_new_report(source_html)
    if strict_new:
        errors = validate_new_report_html(source_html)
        if errors:
            raise ValueError("New report validation failed:\n- " + "\n- ".join(errors))
    body = prepare_report_body(source_html)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report_page(report_date, description, body), encoding="utf-8")


def rewrap_all_reports(reports_dir: Path | None = None) -> int:
    root = reports_dir or Path("docs/reports")
    if not root.is_dir():
        print(f"ERROR: reports directory not found: {root}", file=sys.stderr)
        return 1

    count = 0
    for path in sorted(root.glob("*.html")):
        match = re.match(r"^(\d{4}-\d{2}-\d{2})\.html$", path.name)
        if not match:
            continue
        report_date = datetime.strptime(match.group(1), "%Y-%m-%d")
        content = path.read_text(encoding="utf-8")
        desc_match = META_DESC_PATTERN.search(content)
        description = (
            desc_match.group(1).strip()
            if desc_match and desc_match.group(1).strip()
            else f"Daily AI intelligence briefing for {format_display_date(report_date)}."
        )
        # Historical rewrap: never hard-fail on missing lead hooks
        body = prepare_report_body(content)
        path.write_text(build_report_page(report_date, description, body), encoding="utf-8")
        print(f"Rewrapped {path}")
        count += 1

    print(f"Done — {count} report(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap report body HTML for GitHub Pages")
    parser.add_argument("--rewrap-all", action="store_true", help="Rebuild all docs/reports/*.html")
    parser.add_argument("--date", help="Report date YYYY-MM-DD")
    parser.add_argument("--description", help="Unique meta description")
    parser.add_argument("--input", help="Raw HTML file")
    parser.add_argument("--output", help="Output path (default: docs/reports/DATE.html)")
    parser.add_argument(
        "--allow-historical",
        action="store_true",
        help="Skip new-report lead validation even if data-* hooks are present",
    )
    args = parser.parse_args()

    if args.rewrap_all:
        return rewrap_all_reports()

    if not args.date or not args.description or not args.input:
        parser.error("--date, --description, and --input are required unless --rewrap-all is set")

    try:
        report_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 1

    source = Path(args.input)
    if not source.is_file():
        print(f"ERROR: input not found: {source}", file=sys.stderr)
        return 1

    raw = source.read_text(encoding="utf-8")
    output = Path(args.output) if args.output else Path(f"docs/reports/{args.date}.html")
    try:
        wrap_report_to_path(
            report_date=report_date,
            description=args.description,
            source_html=raw,
            output=output,
            strict_new=(False if args.allow_historical else None),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
