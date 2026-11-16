"""Tests for update_pages_index.py — validates site catalog generation."""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import fromstring

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from update_pages_index import (
    build_feed_xml,
    build_index_html,
    build_archive_html,
    build_search_index,
    build_sitemap_xml,
    build_spectrum_split,
    extract_section_headings,
    format_display_date,
    list_reports,
    parse_report_date,
    read_report_description,
)


# ---------- parse_report_date ----------

class TestParseReportDate:
    def test_valid_filename(self):
        result = parse_report_date("2026-09-20.html")
        assert result is not None
        assert result.year == 2026
        assert result.month == 9
        assert result.day == 20

    def test_invalid_filename(self):
        assert parse_report_date("about.html") is None

    def test_malformed_date(self):
        import pytest
        with pytest.raises(ValueError):
            parse_report_date("2026-13-45.html")


# ---------- format_display_date ----------

class TestFormatDisplayDate:
    def test_formats_correctly(self):
        date = datetime(2026, 9, 20)
        assert format_display_date(date) == "September 20, 2026"


# ---------- list_reports ----------

class TestListReports:
    def test_discovers_reports(self):
        reports = list_reports()
        assert len(reports) >= 34
        # Sorted newest first
        assert reports[0][0] > reports[-1][0]

    def test_report_tuples_have_correct_shape(self):
        reports = list_reports()
        for date, filename, path in reports:
            assert isinstance(date, datetime)
            assert filename.endswith(".html")
            assert path.is_file()


# ---------- read_report_description ----------

class TestReadReportDescription:
    def test_reads_existing_report(self):
        reports = list_reports()
        if reports:
            date, _, path = reports[0]
            desc = read_report_description(path, date)
            assert len(desc) > 10
            assert "AI" in desc or "intelligence" in desc.lower() or len(desc) > 20

    def test_fallback_for_missing_file(self):
        date = datetime(2026, 1, 1)
        desc = read_report_description(Path("/nonexistent.html"), date)
        assert "January 01, 2026" in desc


# ---------- build_index_html ----------

class TestBuildIndexHtml:
    def test_contains_required_elements(self):
        reports = list_reports()
        html = build_index_html(reports)
        assert "<!DOCTYPE html>" in html
        assert "AI Daily Intelligence" in html
        assert "Himanshu Ramavat" in html
        assert "automation-modal-overlay" in html
        assert "search-overlay" in html
        assert "modal.js" in html
        assert "search.js" in html
        assert ">Home<" in html

    def test_spectrum_or_fallback_present(self):
        reports = list_reports()
        html = build_index_html(reports)
        assert "spectrum-split" in html or "home-fallback" in html or "home-empty" in html
        assert "Browse the archive" in html

    def test_lead_and_picks_render_once(self, tmp_path: Path):
        report = tmp_path / "2026-11-16.html"
        report.write_text(
            """
            <article class="report" data-report-date="2026-11-16"
              data-report-title="T" data-reading-minutes="8">
              <div data-report-body>
                <div data-story data-story-id="lead-a" data-story-role="lead"
                     data-story-topics="ai" data-story-dek="Lead dek">
                  <h3 data-story-headline>Unique Lead Headline</h3>
                </div>
                <div data-story data-story-id="pick-a" data-story-role="pick"
                     data-story-topics="startups" data-story-dek="Pick dek">
                  <h3 data-story-headline>Unique Pick Headline</h3>
                </div>
                <div data-story data-story-id="pick-b" data-story-role="pick"
                     data-story-topics="technology">
                  <h3 data-story-headline>Second Pick Headline</h3>
                </div>
                <div data-story data-story-id="topic-a" data-story-topics="ai">
                  <h3 data-story-headline>Topic Story</h3>
                </div>
              </div>
            </article>
            """,
            encoding="utf-8",
        )
        reports = [(datetime(2026, 11, 16), "2026-11-16.html", report)]
        html = build_spectrum_split(reports)
        assert html.count("Unique Lead Headline") == 1
        assert html.count("Unique Pick Headline") == 1
        assert html.count("Second Pick Headline") == 1
        assert html.count("Topic Story") == 1
        assert "spectrum-lead" in html
        assert "spectrum-picks" in html
        assert 'data-topic="ai"' in html

    def test_no_lead_falls_back_to_cta_only(self, tmp_path: Path):
        report = tmp_path / "2026-11-16.html"
        report.write_text("<html><body><p>No stories</p></body></html>", encoding="utf-8")
        reports = [(datetime(2026, 11, 16), "2026-11-16.html", report)]
        html = build_spectrum_split(reports)
        assert "home-fallback" in html
        assert "full-briefing-cta" in html
        assert "story-card" not in html
        assert "Unique Lead" not in html

    def test_empty_topics_omitted(self, tmp_path: Path):
        report = tmp_path / "2026-11-16.html"
        report.write_text(
            """
            <article class="report" data-report-date="2026-11-16"
              data-report-title="T" data-reading-minutes="5">
              <div data-report-body>
                <div data-story data-story-id="lead-a" data-story-role="lead"
                     data-story-topics="ai" data-story-dek="d">
                  <h3 data-story-headline>Only Lead</h3>
                </div>
              </div>
            </article>
            """,
            encoding="utf-8",
        )
        html = build_spectrum_split([(datetime(2026, 11, 16), "2026-11-16.html", report)])
        assert 'data-topic="startups"' not in html
        assert 'data-topic="technology"' not in html
        assert "topic-rail" not in html


# ---------- build_archive_html ----------

class TestBuildArchiveHtml:
    def test_contains_all_reports(self):
        reports = list_reports()
        html = build_archive_html(reports)
        assert f"All reports ({len(reports)})" in html
        assert "Himanshu Ramavat" in html
        assert "archive-search" in html
        assert "archive.js" in html
        assert "archive-row" in html


# ---------- build_feed_xml ----------

class TestBuildFeedXml:
    def test_valid_rss_xml(self):
        reports = list_reports()
        xml_str = build_feed_xml(reports)
        root = fromstring(xml_str)
        assert root.tag == "rss"
        assert root.get("version") == "2.0"
        items = root.findall(".//item")
        assert len(items) == len(reports)

    def test_items_have_required_elements(self):
        reports = list_reports()[:3]
        xml_str = build_feed_xml(reports)
        root = fromstring(xml_str)
        for item in root.findall(".//item"):
            assert item.find("title") is not None
            assert item.find("link") is not None
            assert item.find("pubDate") is not None
            assert item.find("description") is not None


# ---------- build_sitemap_xml ----------

class TestBuildSitemapXml:
    def test_valid_sitemap(self):
        reports = list_reports()
        xml_str = build_sitemap_xml(reports)
        root = fromstring(xml_str)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = root.findall("sm:url", ns)
        # 3 static + all reports
        assert len(urls) == 3 + len(reports)


# ---------- extract_section_headings ----------

class TestExtractSectionHeadings:
    def test_extracts_from_real_report(self):
        reports = list_reports()
        if reports:
            _, _, path = reports[0]
            headings = extract_section_headings(path)
            assert len(headings) >= 5
            assert "Top Developments" in headings

    def test_empty_for_missing_file(self):
        assert extract_section_headings(Path("/nonexistent.html")) == []


# ---------- build_search_index ----------

class TestBuildSearchIndex:
    def test_valid_json(self):
        reports = list_reports()
        index_str = build_search_index(reports)
        data = json.loads(index_str)
        assert len(data) == len(reports)

    def test_entry_shape(self):
        reports = list_reports()[:1]
        data = json.loads(build_search_index(reports))
        entry = data[0]
        assert "date" in entry
        assert "title" in entry
        assert "description" in entry
        assert "dek" in entry
        assert "topics" in entry
        assert "reading_minutes" in entry
        assert "year" in entry
        assert "month" in entry
        assert "href" in entry
        assert "sections" in entry
        assert "url" in entry
        assert entry["url"].startswith("reports/")
        assert entry["href"].startswith("reports/")
