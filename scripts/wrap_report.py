#!/usr/bin/env python3
"""Wrap raw report body HTML with SEO, accessibility, and shared stylesheet."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from site_shell import asset_script, font_links, site_footer, site_nav

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
            f'{match.group(1)}'
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


def build_toc() -> str:
    sections = [
        ("top-developments", "Top Developments"),
        ("emerging-trends", "Emerging AI Trends"),
        ("developer-coding", "Developer & Coding AI"),
        ("agentic-watch", "Agentic AI Watch"),
        ("security-watch", "AI Security Watch"),
        ("research", "Research Worth Reading"),
        ("watch-next", "What I Would Watch Next"),
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


def build_report_page(date: datetime, description: str, body: str) -> str:
    display = format_display_date(date)
    short_date = format_short_date(date)
    iso = format_iso_date(date)
    title = f"AI Daily Intelligence — {display}"
    canonical = f"{PAGES_BASE}/reports/{iso}.html"
    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    intro = (
        "Daily intelligence briefing covering the most important developments across "
        "AI models, agents, developer tools, infrastructure, research, and security."
    )

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
      <span class="report-meta-chip">Daily brief</span>
    </div>
    <p class="intro">{intro}</p>
  </header>
  <div class="report-layout">
    <aside class="report-sidebar" aria-label="Section navigation">
{build_toc()}
    </aside>
    <main class="report-content">
{body}
      <p class="signature">Generated by <strong>AI Intelligence Automation</strong> · <a href="https://github.com/HimanshuRamavat07/HimanshuRamavat07" target="_blank" rel="noopener noreferrer">Source repository</a></p>
    </main>
  </div>
</div>
{site_footer()}
{asset_script("../", "theme.js")}
{asset_script("../", "report.js")}
</body>
</html>
"""


def prepare_report_body(raw_html: str) -> str:
    body = extract_body(raw_html)
    body = strip_wrapped_chrome(raw_html if '<main class="report-content">' in raw_html else body)
    body = add_section_ids(body)
    body = fix_research_headings(body)
    body = fix_stars(body)
    body = fix_external_links(body)
    return body


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

    body = prepare_report_body(source.read_text(encoding="utf-8"))

    output = Path(args.output) if args.output else Path(f"docs/reports/{args.date}.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report_page(report_date, args.description, body), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
