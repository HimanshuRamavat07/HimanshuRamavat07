"""Tests for wrap_report.py — validates the regex-heavy transformation logic."""

import sys
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from wrap_report import (
    add_section_ids,
    extract_body,
    fix_external_links,
    fix_stars,
    strip_wrapped_chrome,
    build_report_page,
)


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
        from datetime import datetime
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
