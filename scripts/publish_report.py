#!/usr/bin/env python3
"""Prepare a daily intelligence report for GitHub Pages publishing."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "docs" / "reports"
UPDATE_INDEX = REPO_ROOT / "scripts" / "update_pages_index.py"
PAGES_BASE = "https://himanshuramavat07.github.io/HimanshuRamavat07"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a daily report into docs/reports/")
    parser.add_argument("--date", required=True, help="Report date in YYYY-MM-DD format")
    parser.add_argument("--html", required=True, help="Path to generated HTML report")
    args = parser.parse_args()

    source = Path(args.html)
    if not source.is_file():
        print(f"ERROR: HTML file not found: {source}", file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    destination = REPORTS_DIR / f"{args.date}.html"
    shutil.copy2(source, destination)
    print(f"Wrote {destination}")

    result = subprocess.run([sys.executable, str(UPDATE_INDEX)], check=False)
    if result.returncode != 0:
        return result.returncode

    report_url = f"{PAGES_BASE}/reports/{args.date}.html"
    index_url = f"{PAGES_BASE}/"
    print(f"Report path: docs/reports/{args.date}.html")
    print(f"Pages URL (after merge): {report_url}")
    print(f"Index URL (after merge): {index_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
