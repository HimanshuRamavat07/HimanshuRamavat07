#!/usr/bin/env python3
"""Rebuild docs/index.html from daily report files in docs/reports/."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "docs" / "reports"
INDEX_PATH = REPO_ROOT / "docs" / "index.html"
PAGES_BASE = "https://himanshuramavat07.github.io/HimanshuRamavat07"
DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")


def parse_report_date(filename: str) -> datetime | None:
    match = DATE_PATTERN.match(filename)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d")


def format_display_date(date: datetime) -> str:
    return date.strftime("%B %d, %Y")


def list_reports() -> list[tuple[datetime, str]]:
    reports: list[tuple[datetime, str]] = []
    if not REPORTS_DIR.exists():
        return reports
    for path in REPORTS_DIR.glob("*.html"):
        parsed = parse_report_date(path.name)
        if parsed:
            reports.append((parsed, path.name))
    reports.sort(key=lambda item: item[0], reverse=True)
    return reports


def build_index_html(reports: list[tuple[datetime, str]]) -> str:
    latest_block = ""
    if reports:
        latest_date, latest_file = reports[0]
        latest_block = f"""
    <section class="latest">
      <p class="label">Latest briefing</p>
      <h2><a href="reports/{latest_file}">AI Daily Intelligence — {format_display_date(latest_date)}</a></h2>
      <p class="meta">Published after merge to main · Updated by daily automation</p>
      <a class="button" href="reports/{latest_file}">Read latest report</a>
    </section>"""

    archive_items = "\n".join(
        f'      <li><a href="reports/{filename}">{format_display_date(date)}</a></li>'
        for date, filename in reports
    )
    archive_section = ""
    if reports:
        archive_section = f"""
    <section class="archive">
      <h2>Archive</h2>
      <ul>
{archive_items}
      </ul>
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
  <title>AI Daily Intelligence</title>
  <meta name="description" content="Daily AI intelligence briefings for developers, AI engineers, and product builders.">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1a1a1a;
      max-width: 760px;
      margin: 0 auto;
      padding: 32px 16px;
      background: #f3f4f6;
    }}
    header, section {{
      background: #fff;
      border-radius: 8px;
      padding: 24px;
      margin-bottom: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin-top: 0; font-size: 20px; color: #1e40af; }}
    .subtitle {{ color: #6b7280; margin: 0; }}
    .label {{ text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; color: #6366f1; font-weight: 700; margin: 0 0 8px; }}
    .meta {{ color: #6b7280; font-size: 14px; }}
    .button {{
      display: inline-block;
      margin-top: 12px;
      background: #2563eb;
      color: #fff !important;
      text-decoration: none;
      padding: 10px 16px;
      border-radius: 6px;
      font-weight: 600;
    }}
    a {{ color: #2563eb; }}
    ul {{ padding-left: 20px; }}
    li {{ margin: 6px 0; }}
    .empty {{ color: #6b7280; }}
    footer {{ color: #9ca3af; font-size: 13px; text-align: center; }}
  </style>
</head>
<body>
  <header>
    <h1>AI Daily Intelligence</h1>
    <p class="subtitle">Signal over volume — curated daily briefings on AI models, agents, developer tools, infrastructure, research, and security.</p>
  </header>
{latest_block}
{archive_section}
  <footer>
    <p>Automated by Cursor · <a href="https://github.com/HimanshuRamavat07/HimanshuRamavat07">View repository</a></p>
  </footer>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild docs/index.html from report files")
    parser.add_argument(
        "--pages-base",
        default=PAGES_BASE,
        help="Public GitHub Pages base URL (used for reference only in future extensions)",
    )
    args = parser.parse_args()
    _ = args.pages_base

    reports = list_reports()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(build_index_html(reports), encoding="utf-8")
    print(f"Updated {INDEX_PATH} with {len(reports)} report(s)")
    if reports:
        latest_date, latest_file = reports[0]
        print(f"Latest: reports/{latest_file} ({format_display_date(latest_date)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
