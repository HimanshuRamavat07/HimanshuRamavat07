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

from extract_stories import (
    APPROVED_TOPICS,
    TOPIC_LABELS,
    assign_homepage,
    extract_report,
)
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


def _paths_for(docs_dir: Path) -> dict[str, Path]:
    return {
        "docs": docs_dir,
        "reports": docs_dir / "reports",
        "archive": docs_dir / "archive",
        "index": docs_dir / "index.html",
        "archive_index": docs_dir / "archive" / "index.html",
        "feed": docs_dir / "feed.xml",
        "sitemap": docs_dir / "sitemap.xml",
        "search_index": docs_dir / "assets" / "search-index.json",
        "search_data": docs_dir / "assets" / "search-data.js",
    }

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


def list_reports(reports_dir: Path | None = None) -> list[tuple[datetime, str, Path]]:
    root = reports_dir or REPORTS_DIR
    reports: list[tuple[datetime, str, Path]] = []
    if not root.exists():
        return reports
    for path in root.glob("*.html"):
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


def report_row(
    *,
    href: str,
    title: str,
    description: str = "",
    compact: bool = False,
    date_label: str = "",
    reading_minutes: int | None = None,
    topics: list[str] | None = None,
    iso_date: str = "",
) -> str:
    desc_block = ""
    if description:
        desc_block = f'\n        <span class="report-row-desc">{html.escape(description)}</span>'
    arrow = icon("arrow_forward", extra_class="report-row-icon")
    if compact:
        return f"""      <a class="report-row" href="{html.escape(href)}">
        <span class="report-row-title">{html.escape(title)}</span>
        {arrow}
      </a>"""
    meta_bits: list[str] = []
    if date_label:
        meta_bits.append(f'<time class="report-row-date" datetime="{html.escape(iso_date)}">{html.escape(date_label)}</time>')
    if reading_minutes:
        meta_bits.append(f'<span class="report-row-mins">{reading_minutes} min</span>')
    if topics:
        topic_labels = ", ".join(TOPIC_LABELS.get(t, t) for t in topics)
        meta_bits.append(f'<span class="report-row-topics">{html.escape(topic_labels)}</span>')
    meta = ""
    if meta_bits:
        meta = f'\n        <span class="report-row-meta">{" · ".join(meta_bits)}</span>'
    topic_attr = html.escape(",".join(topics or ""), quote=True)
    year = iso_date[:4] if iso_date else ""
    month = iso_date[5:7] if len(iso_date) >= 7 else ""
    return f"""      <a class="report-row archive-row" href="{html.escape(href)}"
         data-date="{html.escape(iso_date)}" data-year="{html.escape(year)}"
         data-month="{html.escape(month)}" data-topics="{topic_attr}">
        <span class="report-row-body">
          <span class="report-row-title">{html.escape(title)}</span>{desc_block}{meta}
        </span>
        {arrow}
      </a>"""


def _story_card(story, *, kind: str) -> str:
    dek = f'<p class="story-dek">{html.escape(story.dek)}</p>' if story.dek else ""
    return f"""      <article class="story-card story-card--{html.escape(kind)}" data-story-id="{html.escape(story.id)}">
        <h3 class="story-headline">{html.escape(story.headline)}</h3>
        {dek}
      </article>"""


def build_spectrum_split(reports: list[tuple[datetime, str, Path]]) -> str:
    """Homepage story blocks from the latest report hooks, with CTA fallback."""
    if not reports:
        return """
    <section class="home-empty">
      <p class="empty">No reports published yet. New briefings appear here after each automated run.</p>
    </section>"""

    latest_date, latest_file, latest_path = reports[0]
    report_href = f"reports/{latest_file}"
    cta = (
        f'<p class="full-briefing-cta"><a class="button" href="{html.escape(report_href)}">'
        f"Read the full briefing {icon('arrow_forward', size='18px')}</a></p>"
    )

    raw = latest_path.read_text(encoding="utf-8") if latest_path.is_file() else ""
    extract = extract_report(raw, strict=False)
    blocks = assign_homepage(extract.stories)

    if blocks.lead is None:
        return f"""
    <section class="home-fallback" aria-labelledby="fallback-heading">
      <h2 id="fallback-heading">Today's briefing</h2>
      <p class="home-fallback-copy">Open the full daily report for {html.escape(format_display_date(latest_date))}.</p>
      {cta}
    </section>"""

    lead_html = f"""
    <div class="spectrum-lead">
      <p class="label">Lead</p>
      <h2 class="lead-headline">{html.escape(blocks.lead.headline)}</h2>
      {f'<p class="lead-dek">{html.escape(blocks.lead.dek)}</p>' if blocks.lead.dek else ''}
    </div>"""

    picks_html = ""
    if blocks.picks:
        cards = "\n".join(_story_card(s, kind="pick") for s in blocks.picks)
        picks_html = f"""
    <aside class="spectrum-picks" aria-label="Editor's picks">
      <p class="label">Editor's picks</p>
      <div class="picks-list">
{cards}
      </div>
    </aside>"""

    topic_sections = []
    for slug in APPROVED_TOPICS:
        stories = blocks.topics.get(slug) or []
        if not stories:
            continue
        cards = "\n".join(_story_card(s, kind="topic") for s in stories)
        topic_sections.append(
            f"""
    <section class="topic-section" data-topic="{html.escape(slug)}" aria-labelledby="topic-{html.escape(slug)}">
      <h2 id="topic-{html.escape(slug)}">{html.escape(TOPIC_LABELS[slug])}</h2>
      <div class="topic-stories">
{cards}
      </div>
    </section>"""
        )

    more_html = ""
    if blocks.more:
        cards = "\n".join(_story_card(s, kind="more") for s in blocks.more)
        more_html = f"""
    <section class="more-today" aria-labelledby="more-today-heading">
      <h2 id="more-today-heading">More from today</h2>
      <div class="more-stories">
{cards}
      </div>
    </section>"""

    rail_html = ""
    non_empty_topics = [s for s in APPROVED_TOPICS if blocks.topics.get(s)]
    if len(non_empty_topics) >= 2:
        links = "\n".join(
            f'        <a href="#topic-{html.escape(slug)}">{html.escape(TOPIC_LABELS[slug])}</a>'
            for slug in non_empty_topics
        )
        rail_html = f"""
    <nav class="topic-rail" aria-label="Topics today">
{links}
    </nav>"""

    return f"""
    <section class="spectrum-split" aria-label="Today's briefing highlights">
      <div class="spectrum-split-grid">
{lead_html}
{picks_html}
      </div>
{rail_html}
{"".join(topic_sections)}
{more_html}
      <div class="spectrum-cta">
        {cta}
        <p class="spectrum-date meta">{html.escape(format_display_date(latest_date))}</p>
      </div>
    </section>"""


def build_index_html(reports: list[tuple[datetime, str, Path]]) -> str:
    canonical = f"{PAGES_BASE}/"
    description = (
        "Daily AI-generated summaries covering models, agents, "
        "developer tools, infrastructure, research papers, and security disclosures."
    )
    tagline = (
        "Editorial intelligence on models, agents, coding tools, "
        "infrastructure, research, and security — curated daily."
    )
    spectrum = build_spectrum_split(reports)

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
    <section class="hero hero-editorial">
      <h1>{SITE_TITLE}</h1>
      <p class="subtitle">{tagline}</p>
    </section>
{spectrum}
    <p class="archive-more home-archive-link"><a href="archive/index.html">Browse the archive {icon('arrow_right_alt', size='16px')}</a></p>
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


def report_archive_meta(path: Path, date: datetime) -> dict:
    """Metadata-only fields for archive rows / search index."""
    desc = read_report_description(path, date)
    extract = extract_report(path.read_text(encoding="utf-8"), strict=False) if path.is_file() else None
    topics: list[str] = []
    minutes = None
    dek = desc
    title = f"{SITE_TITLE} — {format_display_date(date)}"
    if extract:
        minutes = extract.reading_minutes
        if extract.title:
            title = extract.title
        seen: set[str] = set()
        for story in extract.stories:
            for slug in story.topics:
                if slug not in seen:
                    seen.add(slug)
                    topics.append(slug)
        if extract.stories and extract.stories[0].dek:
            dek = extract.stories[0].dek
    iso = format_iso_date(date)
    return {
        "date": iso,
        "year": iso[:4],
        "month": iso[5:7],
        "title": title,
        "dek": dek,
        "description": desc,
        "topics": topics,
        "reading_minutes": minutes,
        "href": f"reports/{path.name}" if path.name else "",
        "url": f"reports/{path.name}" if path.name else "",
    }


def build_archive_html(reports: list[tuple[datetime, str, Path]]) -> str:
    canonical = f"{PAGES_BASE}/archive/"
    description = (
        "Archive of daily AI-generated briefings on models, agents, "
        "developer tools, research papers, and security."
    )
    years = sorted({format_iso_date(d)[:4] for d, _, _ in reports}, reverse=True)
    months = [f"{m:02d}" for m in range(1, 13)]
    year_opts = "\n".join(f'          <option value="{y}">{y}</option>' for y in years)
    month_opts = "\n".join(
        f'          <option value="{m}">{datetime(2000, int(m), 1).strftime("%B")}</option>'
        for m in months
    )
    topic_opts = "\n".join(
        f'          <option value="{slug}">{html.escape(label)}</option>'
        for slug, label in TOPIC_LABELS.items()
    )
    # Dedupe month rail labels while preserving order
    seen_months: set[str] = set()
    rail_items: list[str] = []
    for d, _, _ in reports:
        key = format_iso_date(d)[:7]
        if key in seen_months:
            continue
        seen_months.add(key)
        rail_items.append(
            f'        <a class="month-rail-link" href="#m-{key}" data-month-jump="{key}">{key}</a>'
        )
    month_rail = "\n".join(rail_items)

    row_parts: list[str] = []
    last_month = ""
    for date, filename, path in reports:
        meta = report_archive_meta(path, date)
        month_key = meta["date"][:7]
        if month_key != last_month:
            row_parts.append(f'      <div class="archive-month-marker" id="m-{month_key}">{month_key}</div>')
            last_month = month_key
        row_parts.append(
            report_row(
                href=f"../reports/{filename}",
                title=meta["title"],
                description=meta["dek"],
                date_label=format_display_date(date),
                reading_minutes=meta["reading_minutes"],
                topics=meta["topics"],
                iso_date=meta["date"],
            )
        )
    body = "\n".join(row_parts) if reports else '      <p class="empty">No reports yet.</p>'

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
  <main class="site-main archive-layout">
    <section class="hero hero-archive">
      <h1>Report archive</h1>
      <p class="subtitle">Chronological briefings with search and filters. {len(reports)} total.</p>
    </section>
    <div class="archive-controls" data-archive-controls>
      <label class="archive-search-label">
        <span class="visually-hidden">Search archive</span>
        <input type="search" id="archive-search" placeholder="Search titles and deks…" autocomplete="off">
      </label>
      <div class="archive-filters">
        <label>Year
          <select id="archive-year">
            <option value="">All years</option>
{year_opts}
          </select>
        </label>
        <label>Month
          <select id="archive-month">
            <option value="">All months</option>
{month_opts}
          </select>
        </label>
        <label>Topic
          <select id="archive-topic">
            <option value="">All topics</option>
{topic_opts}
          </select>
        </label>
      </div>
    </div>
    <div class="archive-with-rail">
      <nav class="month-rail" aria-label="Months">
{month_rail}
      </nav>
      <section class="archive-section" aria-labelledby="archive-heading">
        <h2 id="archive-heading">All reports ({len(reports)})</h2>
        <div class="report-list" id="archive-report-list">
{body}
        </div>
        <p class="archive-empty" id="archive-empty" hidden>No briefings match these filters.</p>
      </section>
    </div>
  </main>
{site_footer(github_href="https://github.com/HimanshuRamavat07/HimanshuRamavat07", rss_href="../feed.xml")}
{automation_modal()}
{search_overlay(prefix="../")}
{asset_script("../", "theme.js")}
{asset_script("../", "modal.js")}
{asset_script("../", "search-data.js")}
{asset_script("../", "search.js")}
{asset_script("../", "archive.js")}
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
    """Build a metadata-only JSON search index for client-side search/filters."""
    index = []
    for date, filename, path in reports:
        meta = report_archive_meta(path, date)
        sections = extract_section_headings(path)
        index.append({
            "date": meta["date"],
            "year": meta["year"],
            "month": meta["month"],
            "title": meta["title"],
            "description": meta["description"],
            "dek": meta["dek"],
            "topics": meta["topics"],
            "reading_minutes": meta["reading_minutes"],
            "sections": sections,
            "url": f"reports/{filename}",
            "href": f"reports/{filename}",
        })
    return json.dumps(index, ensure_ascii=False, indent=None)


def build_search_data_js(reports: list[tuple[datetime, str, Path]]) -> str:
    """Build an inline JS file that sets window.__SEARCH_INDEX__."""
    index_json = build_search_index(reports)
    return f"window.__SEARCH_INDEX__={index_json};\n"


def rebuild_site_artifacts(*, docs_dir: Path | None = None) -> int:
    paths = _paths_for(docs_dir or DOCS_DIR)
    reports = list_reports(paths["reports"])
    paths["docs"].mkdir(parents=True, exist_ok=True)
    paths["archive"].mkdir(parents=True, exist_ok=True)
    (paths["docs"] / "assets").mkdir(parents=True, exist_ok=True)

    paths["index"].write_text(build_index_html(reports), encoding="utf-8")
    paths["archive_index"].write_text(build_archive_html(reports), encoding="utf-8")
    paths["feed"].write_text(build_feed_xml(reports), encoding="utf-8")
    paths["sitemap"].write_text(build_sitemap_xml(reports), encoding="utf-8")
    paths["search_index"].write_text(build_search_index(reports), encoding="utf-8")
    paths["search_data"].write_text(build_search_data_js(reports), encoding="utf-8")

    print(f"Updated {paths['index']} ({len(reports)} report(s))")
    print(f"Updated {paths['archive_index']}, {paths['feed']}, {paths['sitemap']}")
    print(f"Updated {paths['search_index']}, {paths['search_data']}")
    return 0


def main() -> int:
    return rebuild_site_artifacts()


if __name__ == "__main__":
    raise SystemExit(main())
