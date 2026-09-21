"""Shared HTML shell fragments for AI Daily Intelligence pages."""

from __future__ import annotations

import html
from datetime import datetime, timezone

GITHUB_URL = "https://github.com/HimanshuRamavat07/HimanshuRamavat07"


def font_links() -> str:
    return """  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500;700&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,400,0,0&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">"""


def icon(name: str, *, size: str = "", extra_class: str = "") -> str:
    classes = "material-symbols-outlined"
    if extra_class:
        classes += f" {extra_class}"
    style = f' style="font-size:{size}"' if size else ""
    return f'<span class="{classes}" aria-hidden="true"{style}>{html.escape(name)}</span>'


def theme_toggle_button() -> str:
    return f"""      <button type="button" class="theme-toggle" aria-label="Toggle color theme" title="Toggle theme">
        {icon("light_mode", extra_class="theme-icon theme-icon-sun")}
        {icon("dark_mode", extra_class="theme-icon theme-icon-moon")}
      </button>"""


def search_button() -> str:
    return f"""      <button type="button" class="search-trigger" data-open-search aria-label="Search reports" title="Search (⌘K)">
        {icon("search")}
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
{search_button()}
{theme_toggle_button()}
      </div>
    </div>
  </header>"""


def automation_modal() -> str:
    return f"""  <div class="automation-modal-overlay" id="automation-modal-overlay">
    <div class="automation-modal" role="dialog" aria-labelledby="automation-modal-title" aria-modal="true">
      <button type="button" class="automation-modal-close" aria-label="Close">
        {icon("close", size="20px")}
      </button>
      <h3 id="automation-modal-title">⚙️ How This Works</h3>
      <p class="modal-subtitle">Fully automated AI intelligence publishing pipeline</p>

      <div class="automation-modal-section">
        <h4>Pipeline</h4>
        <ul class="pipeline-steps">
          <li class="pipeline-step"><strong>1. Curate</strong>AI scans the latest AI news, research, and releases daily</li>
          <li class="pipeline-step"><strong>2. Generate</strong>Raw briefing is structured into 8 standardized sections</li>
          <li class="pipeline-step"><strong>3. Wrap &amp; Enrich</strong>SEO meta, JSON-LD schema, TOC sidebar, accessibility fixes</li>
          <li class="pipeline-step"><strong>4. Publish</strong>Auto-deployed to GitHub Pages via CI merge workflow</li>
        </ul>
      </div>

      <div class="automation-modal-section">
        <h4>Tech Stack</h4>
        <ul class="tech-badges">
          <li class="tech-badge">Python</li>
          <li class="tech-badge">GitHub Actions</li>
          <li class="tech-badge">GitHub Pages</li>
          <li class="tech-badge">Cursor AI</li>
          <li class="tech-badge">Vanilla JS</li>
          <li class="tech-badge">RSS 2.0</li>
        </ul>
      </div>

      <div class="automation-modal-section">
        <h4>Publishing Cadence</h4>
        <p>New briefings are published daily, typically covering the prior 24 hours of AI developments across models, agents, developer tools, infrastructure, research, and security.</p>
      </div>

      <div class="automation-modal-section">
        <a class="modal-footer-link" href="{html.escape(GITHUB_URL)}" target="_blank" rel="noopener noreferrer">
          View source on GitHub {icon("open_in_new", size="16px")}
        </a>
      </div>
    </div>
  </div>"""


def search_overlay(*, prefix: str = "") -> str:
    return f"""  <div class="search-overlay" id="search-overlay" data-base-href="{html.escape(prefix)}">
    <div class="search-panel">
      <div class="search-header">
        {icon("search", size="22px")}
        <input type="text" class="search-input" placeholder="Search reports…" autocomplete="off" spellcheck="false">
        <span class="search-kbd">⌘K</span>
        <button type="button" class="search-close" aria-label="Close search">
          {icon("close", size="20px")}
        </button>
      </div>
      <div class="search-body">
        <ul class="search-results"></ul>
        <p class="search-empty" style="display:none"></p>
      </div>
    </div>
  </div>"""


def site_footer(*, github_href: str = GITHUB_URL, rss_href: str | None = None) -> str:
    year = datetime.now(timezone.utc).year
    rss_link = ""
    if rss_href:
        rss_link = f'\n        <a href="{html.escape(rss_href)}">RSS Feed</a>'
    return f"""  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="site-footer-brand">Daily Intelligence</div>
      <div class="site-footer-links">{rss_link}
        <a href="{html.escape(github_href)}" target="_blank" rel="noopener noreferrer">GitHub</a>
        <button type="button" class="automation-info-trigger" data-open-automation-modal>Automation Info</button>
      </div>
      <p class="site-footer-copy">&copy; {year} Himanshu Ramavat &middot; Automated by Cursor</p>
    </div>
  </footer>"""


def asset_script(prefix: str, filename: str) -> str:
    return f'  <script src="{html.escape(prefix)}assets/{html.escape(filename)}" defer></script>'
