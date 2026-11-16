#!/usr/bin/env python3
"""Prepare a daily intelligence report for GitHub Pages publishing."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from update_pages_index import rebuild_site_artifacts  # noqa: E402
from wrap_report import wrap_report_to_path  # noqa: E402

PAGES_BASE = "https://aidaily.is-a.bot"

LIVE_ARTIFACTS = (
    "index.html",
    "archive/index.html",
    "feed.xml",
    "sitemap.xml",
    "assets/search-index.json",
    "assets/search-data.js",
)


def _replace_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".publishing-tmp")
    shutil.copy2(src, tmp)
    tmp.replace(dest)


def swap_live_artifacts(
    replacements: list[tuple[Path, Path]],
    *,
    replace_fn=_replace_file,
) -> None:
    """Replace live files with rollback if any replacement fails mid-sequence."""
    backup_root = Path(tempfile.mkdtemp(prefix="aidaily-live-backup-"))
    backups: list[tuple[Path, Path | None]] = []
    try:
        for _src, dest in replacements:
            if dest.is_file():
                bak = backup_root / dest.relative_to(dest.anchor).as_posix().replace("/", "__")
                # Keep unique flat names under backup_root
                bak = backup_root / f"{len(backups):04d}-{dest.name}"
                shutil.copy2(dest, bak)
                backups.append((dest, bak))
            else:
                backups.append((dest, None))

        for src, dest in replacements:
            replace_fn(src, dest)
    except Exception:
        # Restore prior live artifacts (or remove newly created ones)
        for dest, bak in backups:
            if bak is not None:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bak, dest)
            elif dest.exists():
                dest.unlink()
        raise
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


def publish_atomic(
    *,
    report_date: str,
    source_html: Path,
    description: str,
    repo_root: Path = REPO_ROOT,
    replace_fn=_replace_file,
) -> None:
    """Stage wrap + site rebuild, then replace live artifacts with rollback on failure."""
    date = datetime.strptime(report_date, "%Y-%m-%d")
    live_docs = repo_root / "docs"
    report_name = f"{report_date}.html"

    with tempfile.TemporaryDirectory(prefix="aidaily-publish-") as tmp:
        staging_root = Path(tmp)
        staging_docs = staging_root / "docs"
        # Seed staging with existing docs so index rebuild sees historical reports
        shutil.copytree(live_docs, staging_docs, dirs_exist_ok=True)

        staging_report = staging_docs / "reports" / report_name
        wrap_report_to_path(
            report_date=date,
            description=description,
            source_html=source_html.read_text(encoding="utf-8"),
            output=staging_report,
            strict_new=None,
        )
        rebuild_site_artifacts(docs_dir=staging_docs)

        # Validate staging outputs exist before touching live
        required = [staging_report] + [staging_docs / rel for rel in LIVE_ARTIFACTS]
        missing = [str(p) for p in required if not p.is_file()]
        if missing:
            raise RuntimeError(
                "Staging build incomplete; live site untouched. Missing: " + ", ".join(missing)
            )

        replacements = [(staging_report, live_docs / "reports" / report_name)]
        replacements.extend((staging_docs / rel, live_docs / rel) for rel in LIVE_ARTIFACTS)
        swap_live_artifacts(replacements, replace_fn=replace_fn)


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

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 1

    description = args.description or (
        f"AI Daily Intelligence briefing for {args.date}: top developments in models, "
        "agents, developer tools, infrastructure, research, and security."
    )

    try:
        publish_atomic(
            report_date=args.date,
            source_html=source,
            description=description,
            repo_root=REPO_ROOT,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Publish aborted — no live site artifacts were written.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — surface staging failures cleanly
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Publish aborted — live artifacts restored if a mid-swap failure occurred.", file=sys.stderr)
        return 1

    print(f"Report path: docs/reports/{args.date}.html")
    print(f"Pages URL (after merge): {PAGES_BASE}/reports/{args.date}.html")
    print(f"RSS feed: {PAGES_BASE}/feed.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
