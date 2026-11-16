"""Tests for wrap_report.py — validates the regex-heavy transformation logic."""

import sys
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from wrap_report import (
    add_section_ids,
    build_report_page,
    build_toc_from_body,
    collect_toc_entries,
    ensure_unique_heading_ids,
    extract_body,
    filter_summary_deck_slots,
    fix_external_links,
    fix_stars,
    prepare_report_body,
    strip_wrapped_chrome,
    validate_new_report_html,
    wrap_report_to_path,
)
from datetime import datetime
import pytest
import tempfile
from pathlib import Path


# ---------- fix_stars ----------

class TestFixStars:
    def test_single_star(self):
        html = '<span class="stars">Impact: ⭐</span>'
        result = fix_stars(html)
        assert 'aria-hidden="true"' in result
        assert "Impact: 1 out of 5" in result

    def test_five_stars(self):
        html = '<span class="stars">Impact: ⭐⭐⭐⭐⭐</span>'
        result = fix_stars(html)
        assert "Impact: 5 out of 5" in result

    def test_three_stars(self):
        html = '<span class="stars">Impact: ⭐⭐⭐</span>'
        result = fix_stars(html)
        assert "Impact: 3 out of 5" in result

    def test_no_stars_passthrough(self):
        html = "<p>No stars here</p>"
        result = fix_stars(html)
        assert result == html


# ---------- fix_external_links ----------

class TestFixExternalLinks:
    def test_adds_target_blank(self):
        html = '<a href="https://example.com">Link</a>'
        result = fix_external_links(html)
        assert 'target="_blank"' in result
        assert 'rel="noopener noreferrer"' in result

    def test_preserves_existing_target(self):
        html = '<a href="https://example.com" target="_self">Link</a>'
        result = fix_external_links(html)
        assert 'target="_self"' in result
        assert 'target="_blank"' not in result

    def test_internal_link_unchanged(self):
        html = '<a href="../index.html">Home</a>'
        result = fix_external_links(html)
        assert result == html

    def test_multiple_links(self):
        html = '<a href="https://a.com">A</a> <a href="https://b.com">B</a>'
        result = fix_external_links(html)
        assert result.count('target="_blank"') == 2


# ---------- add_section_ids ----------

class TestAddSectionIds:
    def test_adds_id_to_top_developments(self):
        html = "<h2>🔥 Top Developments</h2>"
        result = add_section_ids(html)
        assert 'id="top-developments"' in result

    def test_adds_id_to_security_watch(self):
        html = "<h2>🔐 AI Security Watch</h2>"
        result = add_section_ids(html)
        assert 'id="security-watch"' in result

    def test_adds_id_to_bottom_line(self):
        html = '<div class="bottom-line">Content</div>'
        result = add_section_ids(html)
        assert 'id="bottom-line"' in result

    def test_all_sections_get_ids(self):
        html = """
        <h2>🔥 Top Developments</h2>
        <h2>🧠 Emerging AI Trends</h2>
        <h2>💻 Developer & Coding AI</h2>
        <h2>🧩 Agentic AI Watch</h2>
        <h2>🔐 AI Security Watch</h2>
        <h2>📚 Research Worth Reading</h2>
        <h2>🚀 What I Would Watch Next</h2>
        <div class="bottom-line">Done</div>
        """
        result = add_section_ids(html)
        expected_ids = [
            "top-developments", "emerging-trends", "developer-coding",
            "agentic-watch", "security-watch", "research",
            "watch-next", "bottom-line",
        ]
        for sid in expected_ids:
            assert f'id="{sid}"' in result, f"Missing id: {sid}"

    def test_adds_id_to_new_watch_next_heading(self):
        html = "<h2>🚀 What to Watch Next</h2>"
        result = add_section_ids(html)
        assert '<h2 id="watch-next">🚀 What to Watch Next</h2>' in result


# ---------- extract_body ----------

class TestExtractBody:
    def test_extracts_from_full_html(self):
        html = '<html><head></head><body><p>Hello</p></body></html>'
        result = extract_body(html)
        assert result == "<p>Hello</p>"

    def test_extracts_from_container(self):
        html = '<html><body><div class="container"><p>Inside</p></div></body></html>'
        result = extract_body(html)
        assert result == "<p>Inside</p>"

    def test_raw_content_passthrough(self):
        html = "<h2>Just content</h2><p>No wrapper</p>"
        result = extract_body(html)
        assert result == html


# ---------- strip_wrapped_chrome ----------

class TestStripWrappedChrome:
    def test_strips_main_wrapper(self):
        html = '<main class="report-content"><h2>Content</h2><p>Text</p></main>'
        result = strip_wrapped_chrome(html)
        assert "<h2>Content</h2>" in result
        assert '<main class="report-content">' not in result

    def test_strips_signature(self):
        html = '<main class="report-content"><h2>Body</h2><p class="signature">By AI</p></main>'
        result = strip_wrapped_chrome(html)
        assert "signature" not in result
        assert "<h2>Body</h2>" in result


# ---------- build_report_page ----------

class TestBuildReportPage:
    def test_output_has_required_elements(self):
        date = datetime(2026, 9, 20)
        result = build_report_page(date, "Test description", "<h2>Test</h2>")

        assert "<!DOCTYPE html>" in result
        assert "September 20, 2026" in result
        assert 'content="Test description"' in result
        assert "Himanshu Ramavat" in result
        assert "automation-modal-overlay" in result
        assert "search-overlay" in result
        assert "modal.js" in result
        assert "search.js" in result
        assert "report.js" in result
        assert "application/ld+json" in result
        assert 'class="report"' in result
        assert "toc-mobile" in result
        assert "data-related-reports" in result


NEW_REPORT_NO_LEAD = """
<article class="report" data-report-date="2026-11-16"
  data-report-title="T" data-reading-minutes="8">
  <div data-report-body>
    <div class="dev-card" data-story data-story-id="only-more" data-story-role="more"
         data-story-topics="ai">
      <h3 data-story-headline>No lead here</h3>
    </div>
  </div>
</article>
"""

NEW_REPORT_WITH_LEAD = """
<article class="report" data-report-date="2026-11-16"
  data-report-title="AI Daily Intelligence — November 16, 2026"
  data-reading-minutes="9">
  <div class="report-body" data-report-body>
    <aside class="summary-deck" data-summary-deck>
      <section data-summary="developments">
        <h2>Today's biggest developments</h2>
        <ul><li>Ship happened</li></ul>
      </section>
      <section data-summary="takeaways">
        <h2>Key takeaways</h2>
      </section>
      <section data-summary="why-it-matters">
        <h2>Why these stories matter</h2>
        <p>Because builders need signal.</p>
      </section>
    </aside>
    <h2>🔥 Top Developments</h2>
    <div class="dev-card" data-story data-story-id="lead-1" data-story-role="lead"
         data-story-topics="ai" data-story-dek="Dek">
      <h3 data-story-headline>Lead story</h3>
      <p><strong>What happened:</strong> Facts.</p>
    </div>
    <h2>Duplicate Title</h2>
    <h3>Duplicate Title</h3>
  </div>
</article>
"""

HISTORICAL_FIXTURE = """
<h2>🔥 Top Developments</h2>
<div class="dev-card">
  <h3>Legacy card</h3>
  <p><strong>What happened:</strong> Old news.</p>
</div>
<h2>🧠 Emerging AI Trends</h2>
<h3>Trend</h3>
<div class="bottom-line"><h3>🎯 Bottom Line</h3><p>Done.</p></div>
"""


class TestNewReportValidation:
    def test_missing_lead_fails_validation(self):
        errors = validate_new_report_html(NEW_REPORT_NO_LEAD)
        assert any("lead" in e.lower() for e in errors)

    def test_wrap_missing_lead_raises_before_write(self, tmp_path: Path):
        out = tmp_path / "2026-11-16.html"
        with pytest.raises(ValueError, match="lead"):
            wrap_report_to_path(
                report_date=datetime(2026, 11, 16),
                description="desc",
                source_html=NEW_REPORT_NO_LEAD,
                output=out,
                strict_new=True,
            )
        assert not out.exists()

    def test_historical_without_hooks_still_wraps(self, tmp_path: Path):
        out = tmp_path / "2026-08-12.html"
        wrap_report_to_path(
            report_date=datetime(2026, 8, 12),
            description="legacy",
            source_html=HISTORICAL_FIXTURE,
            output=out,
            strict_new=False,
        )
        text = out.read_text(encoding="utf-8")
        assert "Legacy card" in text
        assert 'class="report"' in text


class TestTocBoundaries:
    def test_toc_excludes_nav_footer_related_and_summary_deck(self):
        body = """
        <nav class="site-nav"><h2>Site Nav Heading</h2></nav>
        <aside class="summary-deck" data-summary-deck>
          <section data-summary="developments"><h2>Today's biggest developments</h2><ul><li>x</li></ul></section>
        </aside>
        <div data-report-body>
          <h2 id="top-developments">🔥 Top Developments</h2>
          <h3 id="story-a">Story A</h3>
        </div>
        <section class="related-reports" data-related-reports>
          <h2>Related reports</h2>
        </section>
        <footer class="site-footer"><h2>Footer Heading</h2></footer>
        """
        entries = collect_toc_entries(body)
        labels = [label.lower() for _, label in entries]
        assert "site nav heading" not in labels
        assert "footer heading" not in labels
        assert "related reports" not in labels
        assert "today's biggest developments" not in labels
        assert any("top developments" == label.lower() for label in labels)
        assert any("story a" == label.lower() for label in labels)

        toc = build_toc_from_body(body)
        assert "Site Nav Heading" not in toc
        assert "Footer Heading" not in toc
        assert "Related reports" not in toc
        assert "Today's biggest developments" not in toc
        assert "#top-developments" in toc


class TestHeadingIdsAndSummaryDeck:
    def test_duplicate_heading_ids_get_suffixes(self):
        html = "<h2 id=\"same\">One</h2><h3 id=\"same\">Two</h3>"
        result = ensure_unique_heading_ids(html)
        assert 'id="same"' in result
        assert 'id="same-2"' in result

    def test_summary_deck_omits_empty_slots(self):
        html = """
        <aside class="summary-deck" data-summary-deck>
          <section data-summary="developments"><h2>Today's biggest developments</h2><ul><li>A</li></ul></section>
          <section data-summary="takeaways"><h2>Key takeaways</h2></section>
          <section data-summary="why-it-matters"><h2>Why these stories matter</h2><p>Because.</p></section>
        </aside>
        """
        result = filter_summary_deck_slots(html)
        assert 'data-summary="developments"' in result
        assert 'data-summary="why-it-matters"' in result
        assert 'data-summary="takeaways"' not in result

    def test_prepare_applies_summary_filter(self):
        body = prepare_report_body(NEW_REPORT_WITH_LEAD)
        assert 'data-summary="takeaways"' not in body
        assert 'data-summary="developments"' in body


class TestAtomicPublishFailure:
    def test_missing_lead_leaves_live_docs_untouched(self, tmp_path: Path):
        import shutil
        from publish_report import publish_atomic

        repo = tmp_path / "repo"
        docs = repo / "docs"
        (docs / "reports").mkdir(parents=True)
        (docs / "archive").mkdir(parents=True)
        (docs / "assets").mkdir(parents=True)
        # Minimal live artifacts
        (docs / "index.html").write_text("LIVE_INDEX", encoding="utf-8")
        (docs / "archive" / "index.html").write_text("LIVE_ARCHIVE", encoding="utf-8")
        (docs / "feed.xml").write_text("<rss/>", encoding="utf-8")
        (docs / "sitemap.xml").write_text("<urlset/>", encoding="utf-8")
        (docs / "assets" / "search-index.json").write_text("[]", encoding="utf-8")
        (docs / "assets" / "search-data.js").write_text("window.__SEARCH_INDEX__=[];\n", encoding="utf-8")
        (docs / "assets" / "style.css").write_text("body{}", encoding="utf-8")
        # Seed one historical report so rebuild has something if it ran
        (docs / "reports" / "2026-01-01.html").write_text("<html>old</html>", encoding="utf-8")

        bad = tmp_path / "bad.html"
        bad.write_text(NEW_REPORT_NO_LEAD, encoding="utf-8")

        with pytest.raises(ValueError):
            publish_atomic(
                report_date="2026-11-16",
                source_html=bad,
                description="should fail",
                repo_root=repo,
            )

        assert not (docs / "reports" / "2026-11-16.html").exists()
        assert (docs / "index.html").read_text(encoding="utf-8") == "LIVE_INDEX"
        assert (docs / "archive" / "index.html").read_text(encoding="utf-8") == "LIVE_ARCHIVE"
