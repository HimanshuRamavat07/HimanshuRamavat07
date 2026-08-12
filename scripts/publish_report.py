#!/usr/bin/env python3
"""Prepare a daily intelligence report for GitHub Pages publishing."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WRAP_REPORT = REPO_ROOT / "scripts" / "wrap_report.py"
UPDATE_SITE = REPO_ROOT / "scripts" / "update_pages_index.py"
PAGES_BASE = "https://himanshuramavat07.github.io/HimanshuRamavat07"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a daily report into docs/reports/")
    parser.add_argument("--date", required=True, help="Report date in YYYY-MM-DD format")
    parser.add_argument("--html", required=True, help="Path to generated HTML report")
    parser.add_argument(
        "--description",
        help="Unique meta description (defaults to generic daily summary)",
    )
    args = parser.parse_args()

    source = Path(args.html)
    if not source.is_file():
        print(f"ERROR: HTML file not found: {source}", file=sys.stderr)
        return 1

    description = args.description or (
        f"AI Daily Intelligence briefing for {args.date}: top developments in models, "
        "agents, developer tools, infrastructure, research, and security."
    )
    destination = REPO_ROOT / "docs" / "reports" / f"{args.date}.html"

    wrap_cmd = [
        sys.executable,
        str(WRAP_REPORT),
        "--date",
        args.date,
        "--description",
        description,
        "--input",
        str(source),
        "--output",
        str(destination),
    ]
    if subprocess.run(wrap_cmd, check=False).returncode != 0:
        return 1

    if subprocess.run([sys.executable, str(UPDATE_SITE)], check=False).returncode != 0:
        return 1

    print(f"Report path: docs/reports/{args.date}.html")
    print(f"Pages URL (after merge): {PAGES_BASE}/reports/{args.date}.html")
    print(f"RSS feed: {PAGES_BASE}/feed.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
