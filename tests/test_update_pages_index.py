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

    def test_recent_limit(self):
        reports = list_reports()
        html = build_index_html(reports)
        assert "report-row" in html
        assert f"View all {len(reports)} reports" in html


# ---------- build_archive_html ----------

class TestBuildArchiveHtml:
    def test_contains_all_reports(self):
        reports = list_reports()
        html = build_archive_html(reports)
        assert f"All reports ({len(reports)})" in html
        assert "Himanshu Ramavat" in html


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
        assert "sections" in entry
        assert "url" in entry
        assert entry["url"].startswith("reports/")
