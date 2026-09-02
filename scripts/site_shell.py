"""Shared HTML shell fragments for AI Daily Intelligence pages."""

from __future__ import annotations

import html
from datetime import datetime, timezone

GITHUB_URL = "https://github.com/HimanshuRamavat07/HimanshuRamavat07"


def font_links() -> str:
    return """  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">"""


def theme_toggle_button() -> str:
    return """      <button type="button" class="theme-toggle" aria-label="Toggle color theme" title="Toggle theme">
        <span class="theme-icon theme-icon-sun" aria-hidden="true">☀</span>
        <span class="theme-icon theme-icon-moon" aria-hidden="true">☾</span>
      </button>"""


def site_nav(*, home_href: str, archive_href: str, rss_href: str, active: str) -> str:
    home_active = ' class="is-active"' if active == "home" else ""
    archive_active = ' class="is-active"' if active == "archive" else ""
    return f"""  <header class="site-nav">
    <div class="site-nav-inner">
      <a class="site-logo" href="{html.escape(home_href)}">Daily Intelligence</a>
      <div class="site-nav-right">
        <nav class="site-nav-links" aria-label="Site">
          <a{home_active} href="{html.escape(home_href)}">Latest</a>
          <a{archive_active} href="{html.escape(archive_href)}">Archive</a>
          <a href="{html.escape(rss_href)}">RSS</a>
        </nav>
{theme_toggle_button()}
      </div>
    </div>
  </header>"""


def site_footer(*, github_href: str = GITHUB_URL) -> str:
    year = datetime.now(timezone.utc).year
    return f"""  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="site-footer-brand">Daily Intelligence</div>
      <div class="site-footer-links">
        <a href="{html.escape(github_href)}" target="_blank" rel="noopener noreferrer">GitHub</a>
      </div>
      <p class="site-footer-copy">© {year} Daily Intelligence · Automated by Cursor</p>
    </div>
  </footer>"""


def asset_script(prefix: str, filename: str) -> str:
    return f'  <script src="{html.escape(prefix)}assets/{html.escape(filename)}" defer></script>'
