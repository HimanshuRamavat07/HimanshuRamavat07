#!/usr/bin/env python3
"""Rebuild site artifacts: index, archive, feed.xml, and sitemap.xml."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = DOCS_DIR / "reports"
ARCHIVE_DIR = DOCS_DIR / "archive"
INDEX_PATH = DOCS_DIR / "index.html"
ARCHIVE_INDEX_PATH = ARCHIVE_DIR / "index.html"
FEED_PATH = DOCS_DIR / "feed.xml"
SITEMAP_PATH = DOCS_DIR / "sitemap.xml"

PAGES_BASE = "https://himanshuramavat07.github.io/HimanshuRamavat07"
SITE_TITLE = "AI Daily Intelligence"
ARCHIVE_RECENT_LIMIT = 10
DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")
META_DESC_PATTERN = re.compile(
    r'<meta\s+name="description"\s+content="([^"]*)"\s*/?>',
    re.IGNORECASE,
)


def parse_report_date(filename: str) -> datetime | None:
    match = DATE_PATTERN.match(filename)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d")


def format_display_date(date: datetime) -> str:
    return date.strftime("%B %d, %Y")


def format_iso_date(date: datetime) -> str:
    return date.strftime("%Y-%m-%d")


def list_reports() -> list[tuple[datetime, str, Path]]:
    reports: list[tuple[datetime, str, Path]] = []
    if not REPORTS_DIR.exists():
        return reports
    for path in REPORTS_DIR.glob("*.html"):
        parsed = parse_report_date(path.name)
        if parsed:
            reports.append((parsed, path.name, path))
    reports.sort(key=lambda item: item[0], reverse=True)
    return reports


def read_report_description(path: Path, date: datetime) -> str:
    if path.is_file():
        content = path.read_text(encoding="utf-8")
        match = META_DESC_PATTERN.search(content)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return (
        f"Daily AI intelligence briefing for {format_display_date(date)} — "
        "models, agents, developer tools, infrastructure, research, and security."
    )


def og_tags(*, title: str, description: str, url: str) -> str:
    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    safe_url = html.escape(url)
    return f"""  <link rel="canonical" href="{safe_url}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{safe_title}">
  <meta property="og:description" content="{safe_desc}">
  <meta property="og:url" content="{safe_url}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{safe_title}">
  <meta name="twitter:description" content="{safe_desc}">"""


def build_index_html(reports: list[tuple[datetime, str, Path]]) -> str:
    canonical = f"{PAGES_BASE}/"
    description = (
        "Daily AI intelligence briefings for developers, AI engineers, and product builders. "
        "Models, agents, developer tools, infrastructure, research, and security."
    )

    latest_block = ""
    if reports:
        latest_date, latest_file, _ = reports[0]
        latest_block = f"""
    <section class="latest" aria-labelledby="latest-heading">
      <p class="label">Latest briefing</p>
      <h2 id="latest-heading">AI Daily Intelligence — {format_display_date(latest_date)}</h2>
      <p class="meta">Published after merge to main · Updated by daily automation</p>
      <a class="button" href="reports/{latest_file}">Read latest report</a>
    </section>"""

    recent = reports[:ARCHIVE_RECENT_LIMIT]
    archive_items = "\n".join(
        f'        <li><a href="reports/{filename}">{format_display_date(date)}</a></li>'
        for date, filename, _ in recent
    )
    archive_more = ""
    if len(reports) > ARCHIVE_RECENT_LIMIT:
        archive_more = (
            f'\n      <p class="archive-more"><a href="archive/index.html">'
            f"View all {len(reports)} reports →</a></p>"
        )

    archive_section = ""
    if reports:
        archive_section = f"""
    <section class="archive" aria-labelledby="archive-heading">
      <h2 id="archive-heading">Recent reports</h2>
      <ul>
{archive_items}
      </ul>{archive_more}
    </section>"""
    else:
        archive_section = """
    <section class="archive">
      <h2>Archive</h2>
      <p class="empty">No reports published yet. Merge a daily intelligence PR to add the first briefing.</p>
    </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{SITE_TITLE}</title>
  <meta name="description" content="{html.escape(description)}">
{og_tags(title=SITE_TITLE, description=description, url=canonical)}
  <link rel="alternate" type="application/rss+xml" title="{SITE_TITLE} RSS" href="feed.xml">
  <link rel="stylesheet" href="assets/style.css">
</head>
<body class="page-home">
  <header>
    <h1>{SITE_TITLE}</h1>
    <p class="subtitle">Signal over volume — curated daily briefings on AI models, agents, developer tools, infrastructure, research, and security.</p>
  </header>
{latest_block}
{archive_section}
  <footer class="site-footer">
    <p>Automated by Cursor · <a href="https://github.com/HimanshuRamavat07/HimanshuRamavat07">View repository</a> · <a href="feed.xml">RSS feed</a></p>
  </footer>
</body>
</html>
"""


def build_archive_html(reports: list[tuple[datetime, str, Path]]) -> str:
    canonical = f"{PAGES_BASE}/archive/"
    description = "Full archive of AI Daily Intelligence daily briefings."
    items = "\n".join(
        f'        <li><a href="../reports/{filename}">{format_display_date(date)}</a></li>'
        for date, filename, _ in reports
    )
    body = items if reports else '        <li class="empty">No reports yet.</li>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Archive — {SITE_TITLE}</title>
  <meta name="description" content="{html.escape(description)}">
{og_tags(title=f"Archive — {SITE_TITLE}", description=description, url=canonical)}
  <link rel="alternate" type="application/rss+xml" title="{SITE_TITLE} RSS" href="../feed.xml">
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body class="page-home">
  <header>
    <h1>Report archive</h1>
    <p class="subtitle"><a href="../index.html">← Back to homepage</a></p>
  </header>
  <section class="archive">
    <h2>All reports ({len(reports)})</h2>
    <ul>
{body}
    </ul>
  </section>
  <footer class="site-footer">
    <p><a href="../index.html">Home</a> · <a href="../feed.xml">RSS feed</a></p>
  </footer>
</body>
</html>
"""


def build_feed_xml(reports: list[tuple[datetime, str, Path]]) -> str:
    channel = Element("rss", version="2.0")
    channel_el = SubElement(channel, "channel")
    SubElement(channel_el, "title").text = SITE_TITLE
    SubElement(channel_el, "link").text = PAGES_BASE + "/"
    SubElement(channel_el, "description").text = (
        "Daily AI intelligence briefings for developers and AI product builders."
    )
    SubElement(channel_el, "language").text = "en-us"
    SubElement(channel_el, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc), usegmt=True
    )

    for date, filename, path in reports:
        report_url = f"{PAGES_BASE}/reports/{filename}"
        item = SubElement(channel_el, "item")
        SubElement(item, "title").text = f"AI Daily Intelligence — {format_display_date(date)}"
        SubElement(item, "link").text = report_url
        SubElement(item, "guid", isPermaLink="true").text = report_url
        SubElement(item, "pubDate").text = format_datetime(
            date.replace(tzinfo=timezone.utc), usegmt=True
        )
        SubElement(item, "description").text = read_report_description(path, date)

    xml_bytes = tostring(channel, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def build_sitemap_xml(reports: list[tuple[datetime, str, Path]]) -> str:
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    static_urls = [
        (f"{PAGES_BASE}/", "daily"),
        (f"{PAGES_BASE}/feed.xml", "daily"),
        (f"{PAGES_BASE}/archive/", "weekly"),
    ]
    for loc, freq in static_urls:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = loc
        SubElement(url_el, "changefreq").text = freq

    for date, filename, _ in reports:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = f"{PAGES_BASE}/reports/{filename}"
        SubElement(url_el, "lastmod").text = format_iso_date(date)
        SubElement(url_el, "changefreq").text = "never"

    xml_bytes = tostring(urlset, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def main() -> int:
    reports = list_reports()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    INDEX_PATH.write_text(build_index_html(reports), encoding="utf-8")
    ARCHIVE_INDEX_PATH.write_text(build_archive_html(reports), encoding="utf-8")
    FEED_PATH.write_text(build_feed_xml(reports), encoding="utf-8")
    SITEMAP_PATH.write_text(build_sitemap_xml(reports), encoding="utf-8")

    print(f"Updated {INDEX_PATH} ({len(reports)} report(s))")
    print(f"Updated {ARCHIVE_INDEX_PATH}, {FEED_PATH}, {SITEMAP_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
