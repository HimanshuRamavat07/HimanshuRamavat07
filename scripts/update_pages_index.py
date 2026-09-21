#!/usr/bin/env python3
"""Rebuild site artifacts: index, archive, feed.xml, and sitemap.xml."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from site_shell import asset_script, automation_modal, font_links, icon, search_overlay, site_footer, site_nav

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = DOCS_DIR / "reports"
ARCHIVE_DIR = DOCS_DIR / "archive"
INDEX_PATH = DOCS_DIR / "index.html"
ARCHIVE_INDEX_PATH = ARCHIVE_DIR / "index.html"
FEED_PATH = DOCS_DIR / "feed.xml"
SITEMAP_PATH = DOCS_DIR / "sitemap.xml"
SEARCH_INDEX_PATH = DOCS_DIR / "assets" / "search-index.json"
SEARCH_DATA_JS_PATH = DOCS_DIR / "assets" / "search-data.js"

PAGES_BASE = "https://aidaily.is-a.bot"
SITE_TITLE = "AI Daily Intelligence"
HOME_RECENT_LIMIT = 5
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
        f"AI-generated briefing for {format_display_date(date)}: "
        "models, agents, developer tools, research papers, and security disclosures."
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


def report_row(*, href: str, title: str, description: str = "", compact: bool = False) -> str:
    desc_block = ""
    if description:
        desc_block = f'\n        <span class="report-row-desc">{html.escape(description)}</span>'
    arrow = icon("arrow_forward", extra_class="report-row-icon")
    if compact:
        return f"""      <a class="report-row" href="{html.escape(href)}">
        <span class="report-row-title">{html.escape(title)}</span>
        {arrow}
      </a>"""
    return f"""      <a class="report-row" href="{html.escape(href)}">
        <span class="report-row-body">
          <span class="report-row-title">{html.escape(title)}</span>{desc_block}
        </span>
        {arrow}
      </a>"""


def build_index_html(reports: list[tuple[datetime, str, Path]]) -> str:
    canonical = f"{PAGES_BASE}/"
    description = (
        "Daily AI-generated summaries covering models, agents, "
        "developer tools, infrastructure, research papers, and security disclosures."
    )
    tagline = (
        "Daily AI-generated briefings on models, agents, "
        "coding tools, infrastructure, research papers, and security disclosures."
    )

    latest_block = ""
    if reports:
        latest_date, latest_file, _latest_path = reports[0]
        latest_title = f"{SITE_TITLE} — {format_display_date(latest_date)}"
        latest_block = f"""
    <section class="latest group" aria-labelledby="latest-heading">
      <div class="latest-inner">
        <div class="latest-content">
          <div class="latest-heading-row">
            <p class="label">Latest Briefing</p>
            <div class="signal-bars" aria-hidden="true">
              <span></span><span></span><span></span>
            </div>
          </div>
          <h2 id="latest-heading"><a href="reports/{latest_file}">{html.escape(latest_title)}</a></h2>
          <p class="meta">{icon("schedule", size="16px")} Drafted by AI from linked sources · Verify before acting</p>
        </div>
        <a class="button" href="reports/{latest_file}">Read latest report {icon("arrow_forward", size="18px")}</a>
      </div>
    </section>"""

    recent = reports[:HOME_RECENT_LIMIT]
    archive_rows = "\n".join(
        report_row(
            href=f"reports/{filename}",
            title=format_display_date(date),
            compact=True,
        )
        for date, filename, _ in recent
    )
    archive_more = ""
    if len(reports) > HOME_RECENT_LIMIT:
        archive_more = (
            f'\n      <p class="archive-more"><a href="archive/index.html">'
            f"View all {len(reports)} reports {icon('arrow_right_alt', size='16px')}</a></p>"
        )

    archive_section = ""
    if reports:
        archive_section = f"""
    <section class="archive-section" aria-labelledby="archive-heading">
      <h2 id="archive-heading">Recent reports</h2>
      <div class="report-list">
{archive_rows}
      </div>{archive_more}
    </section>"""
    else:
        archive_section = """
    <section class="archive-section">
      <h2>Archive</h2>
      <p class="empty">No reports published yet. New briefings appear here after each automated run.</p>
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
{font_links()}
  <link rel="stylesheet" href="assets/style.css">
</head>
<body class="page-home">
{site_nav(home_href="index.html", archive_href="archive/index.html", rss_href="feed.xml", active="home")}
  <main class="site-main">
    <section class="hero">
      <h1>{SITE_TITLE}</h1>
      <p class="subtitle">{tagline}</p>
    </section>
{latest_block}
{archive_section}
  </main>
{site_footer(github_href="https://github.com/HimanshuRamavat07/HimanshuRamavat07", rss_href="feed.xml")}
{automation_modal()}
{search_overlay()}
{asset_script("", "theme.js")}
{asset_script("", "modal.js")}
{asset_script("", "search-data.js")}
{asset_script("", "search.js")}
</body>
</html>
"""


def build_archive_html(reports: list[tuple[datetime, str, Path]]) -> str:
    canonical = f"{PAGES_BASE}/archive/"
    description = (
        "Archive of daily AI-generated briefings on models, agents, "
        "developer tools, research papers, and security."
    )
    rows = "\n".join(
        report_row(
            href=f"../reports/{filename}",
            title=format_display_date(date),
            description=read_report_description(path, date),
        )
        for date, filename, path in reports
    )
    body = rows if reports else '      <p class="empty">No reports yet.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Archive — {SITE_TITLE}</title>
  <meta name="description" content="{html.escape(description)}">
{og_tags(title=f"Archive — {SITE_TITLE}", description=description, url=canonical)}
  <link rel="alternate" type="application/rss+xml" title="{SITE_TITLE} RSS" href="../feed.xml">
{font_links()}
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body class="page-home page-archive">
{site_nav(home_href="../index.html", archive_href="index.html", rss_href="../feed.xml", active="archive")}
  <main class="site-main">
    <section class="hero">
      <h1>Report archive</h1>
      <p class="subtitle"><a href="../index.html">← Back to homepage</a></p>
    </section>
    <section class="archive-section" aria-labelledby="archive-heading">
      <h2 id="archive-heading">All reports ({len(reports)})</h2>
      <div class="report-list">
{body}
      </div>
    </section>
  </main>
{site_footer(github_href="https://github.com/HimanshuRamavat07/HimanshuRamavat07", rss_href="../feed.xml")}
{automation_modal()}
{search_overlay(prefix="../")}
{asset_script("../", "theme.js")}
{asset_script("../", "modal.js")}
{asset_script("../", "search-data.js")}
{asset_script("../", "search.js")}
</body>
</html>
"""


def build_feed_xml(reports: list[tuple[datetime, str, Path]]) -> str:
    channel = Element("rss", version="2.0")
    channel_el = SubElement(channel, "channel")
    SubElement(channel_el, "title").text = SITE_TITLE
    SubElement(channel_el, "link").text = PAGES_BASE + "/"
    SubElement(channel_el, "description").text = (
        "Daily AI-generated briefings on models, agents, developer tools, research papers, and security."
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


SECTION_HEADING_PATTERN = re.compile(r"<h2[^>]*>([^<]*)</h2>", re.IGNORECASE)


def extract_section_headings(path: Path) -> list[str]:
    """Extract h2 section headings from a report for search indexing."""
    if not path.is_file():
        return []
    content = path.read_text(encoding="utf-8")
    headings: list[str] = []
    for match in SECTION_HEADING_PATTERN.finditer(content):
        text = match.group(1).strip()
        # Strip emoji prefixes for cleaner search
        clean = re.sub(r"^[\U0001f300-\U0001fAFF\U00002702-\U000027B0\U0001f900-\U0001f9FF]+\s*", "", text)
        if clean and clean not in ("On this page",):
            headings.append(clean)
    return headings


def build_search_index(reports: list[tuple[datetime, str, Path]]) -> str:
    """Build a JSON search index for client-side search."""
    index = []
    for date, filename, path in reports:
        title = f"AI Daily Intelligence — {format_display_date(date)}"
        description = read_report_description(path, date)
        sections = extract_section_headings(path)
        url = f"reports/{filename}"
        index.append({
            "date": format_iso_date(date),
            "title": title,
            "description": description,
            "sections": sections,
            "url": url,
        })
    return json.dumps(index, ensure_ascii=False, indent=None)


def build_search_data_js(reports: list[tuple[datetime, str, Path]]) -> str:
    """Build an inline JS file that sets window.__SEARCH_INDEX__."""
    index_json = build_search_index(reports)
    return f"window.__SEARCH_INDEX__={index_json};\n"


def main() -> int:
    reports = list_reports()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    INDEX_PATH.write_text(build_index_html(reports), encoding="utf-8")
    ARCHIVE_INDEX_PATH.write_text(build_archive_html(reports), encoding="utf-8")
    FEED_PATH.write_text(build_feed_xml(reports), encoding="utf-8")
    SITEMAP_PATH.write_text(build_sitemap_xml(reports), encoding="utf-8")
    SEARCH_INDEX_PATH.write_text(build_search_index(reports), encoding="utf-8")
    SEARCH_DATA_JS_PATH.write_text(build_search_data_js(reports), encoding="utf-8")

    print(f"Updated {INDEX_PATH} ({len(reports)} report(s))")
    print(f"Updated {ARCHIVE_INDEX_PATH}, {FEED_PATH}, {SITEMAP_PATH}")
    print(f"Updated {SEARCH_INDEX_PATH}, {SEARCH_DATA_JS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
