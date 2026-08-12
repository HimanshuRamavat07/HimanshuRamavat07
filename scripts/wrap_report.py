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

PAGES_BASE = "https://himanshuramavat07.github.io/HimanshuRamavat07"

STAR_PATTERN = re.compile(r'(<span class="stars">Impact:\s*)([⭐]+)(</span>)')
EXTERNAL_LINK_PATTERN = re.compile(
    r'<a\s+([^>]*?)href="(https?://[^"]+)"([^>]*)>',
    re.IGNORECASE,
)


def format_display_date(date: datetime) -> str:
    return date.strftime("%B %d, %Y")


def format_iso_date(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


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
    items = "\n".join(f'    <li><a href="#{sid}">{label}</a></li>' for sid, label in sections)
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


def strip_wrapped_chrome(body: str) -> str:
    body = re.sub(r"<p class=\"intro\">.*?</p>\s*", "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<p class="meta"><a href="\.\./index\.html">.*?</a></p>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r"<h1>🤖 AI Daily Intelligence —.*?</h1>\s*", "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<nav class="toc".*?</nav>\s*', "", body, count=1, flags=re.DOTALL)
    body = re.sub(r'<p class="signature">.*?</p>\s*', "", body, count=1, flags=re.DOTALL)
    return body.strip()


def build_report_page(date: datetime, description: str, body: str) -> str:
    display = format_display_date(date)
    iso = format_iso_date(date)
    title = f"AI Daily Intelligence — {display}"
    canonical = f"{PAGES_BASE}/reports/{iso}.html"
    safe_title = html.escape(title)
    safe_desc = html.escape(description)

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
  <link rel="stylesheet" href="../assets/style.css">
  <script type="application/ld+json">
{json_ld}
  </script>
</head>
<body class="report-page">
<div class="container">
<p class="intro">Daily intelligence briefing covering the most important developments across AI models, agents, developer tools, infrastructure, research, and security.</p>
<p class="meta"><a href="../index.html">← Back to archive</a></p>

<h1>🤖 AI Daily Intelligence — {display}</h1>
{build_toc()}
{body}
<p class="signature">Generated by <strong>AI Intelligence Automation</strong> · <a href="https://github.com/HimanshuRamavat07/HimanshuRamavat07" target="_blank" rel="noopener noreferrer">Source repository</a></p>
</div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Wrap report body HTML for GitHub Pages")
    parser.add_argument("--date", required=True, help="Report date YYYY-MM-DD")
    parser.add_argument("--description", required=True, help="Unique meta description")
    parser.add_argument("--input", required=True, help="Raw HTML file")
    parser.add_argument("--output", help="Output path (default: docs/reports/DATE.html)")
    args = parser.parse_args()

    try:
        report_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 1

    source = Path(args.input)
    if not source.is_file():
        print(f"ERROR: input not found: {source}", file=sys.stderr)
        return 1

    body = extract_body(source.read_text(encoding="utf-8"))
    body = strip_wrapped_chrome(body)
    body = add_section_ids(body)
    body = fix_research_headings(body)
    body = fix_stars(body)
    body = fix_external_links(body)

    output = Path(args.output) if args.output else Path(f"docs/reports/{args.date}.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report_page(report_date, args.description, body), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
