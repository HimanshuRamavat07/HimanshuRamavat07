"""Tests for story extraction contract (design §5)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from extract_stories import (
    APPROVED_TOPICS,
    HomepageBlocks,
    ReportExtract,
    Story,
    assign_homepage,
    extract_report,
    validate_new_report,
)


HOOKED_REPORT = """
<article class="report"
  data-report-date="2026-11-16"
  data-report-title="AI Daily Intelligence — November 16, 2026"
  data-reading-minutes="11">
  <div class="report-body" data-report-body>
    <div class="dev-card" data-story data-story-id="lead-story" data-story-role="lead"
         data-story-topics="ai,software-development"
         data-story-dek="Lead dek for the homepage.">
      <h3 data-story-headline>Lead headline about models</h3>
      <p><strong>What happened:</strong> Something big shipped.</p>
    </div>
    <div class="dev-card" data-story data-story-id="pick-one" data-story-role="pick"
         data-story-topics="startups" data-story-dek="Pick one dek.">
      <h3 data-story-headline>Pick one headline</h3>
    </div>
    <div class="dev-card" data-story data-story-id="pick-two" data-story-role="pick"
         data-story-topics="technology">
      <h3 data-story-headline>Pick two headline</h3>
      <p><strong>What happened:</strong> Fallback dek from what happened.</p>
    </div>
    <div class="dev-card" data-story data-story-id="topic-only" data-story-role="more"
         data-story-topics="ai,bogus-topic,software-development">
      <h3 data-story-headline>Topic only story</h3>
    </div>
    <div class="dev-card" data-story data-story-id="orphan-more"
         data-story-topics="technology" data-story-dek="More dek.">
      <h3 data-story-headline>More from today story</h3>
    </div>
  </div>
</article>
"""


class TestExtractReportMeta:
    def test_iso_date_and_minutes(self):
        extract = extract_report(HOOKED_REPORT, strict=True)
        assert extract.date == "2026-11-16"
        assert extract.title.startswith("AI Daily Intelligence")
        assert extract.reading_minutes == 11
        assert extract.errors == []

    def test_invalid_date_recorded(self):
        html = HOOKED_REPORT.replace('data-report-date="2026-11-16"', 'data-report-date="11-16-2026"')
        extract = extract_report(html, strict=True)
        assert any("date" in e.lower() for e in extract.errors)

    def test_non_positive_minutes_recorded(self):
        html = HOOKED_REPORT.replace('data-reading-minutes="11"', 'data-reading-minutes="0"')
        extract = extract_report(html, strict=True)
        assert any("reading" in e.lower() for e in extract.errors)


class TestStoryFields:
    def test_unique_story_ids(self):
        extract = extract_report(HOOKED_REPORT, strict=True)
        ids = [s.id for s in extract.stories]
        assert len(ids) == len(set(ids))

    def test_role_enum(self):
        extract = extract_report(HOOKED_REPORT, strict=True)
        roles = {s.role for s in extract.stories}
        assert roles <= {"lead", "pick", "more", None}
        assert "lead" in roles
        assert "pick" in roles

    def test_invalid_taxonomy_slugs_silently_ignored_not_hard_reject(self):
        """Unknown slugs are dropped; approved ones kept. Must NOT hard-reject the story."""
        extract = extract_report(HOOKED_REPORT, strict=True)
        topic_story = next(s for s in extract.stories if s.id == "topic-only")
        assert "bogus-topic" not in topic_story.topics
        assert topic_story.topics == ["ai", "software-development"]
        assert topic_story.primary_topic == "ai"
        # Distinct from hard-reject: story remains extractable; no slug-rejection error
        assert not any("bogus" in e.lower() or "unknown slug" in e.lower() for e in extract.errors)
        assert not any("taxonomy" in e.lower() and "reject" in e.lower() for e in extract.errors)

    def test_approved_topics_constant(self):
        assert APPROVED_TOPICS == (
            "ai",
            "software-development",
            "startups",
            "technology",
        )


class TestValidateNewReport:
    def test_exactly_one_lead_required_strict(self):
        extract = extract_report(HOOKED_REPORT, strict=True)
        assert validate_new_report(extract) == []

        no_lead = HOOKED_REPORT.replace('data-story-role="lead"', 'data-story-role="more"')
        extract_no = extract_report(no_lead, strict=True)
        errors = validate_new_report(extract_no)
        assert any("lead" in e.lower() for e in errors)

    def test_picks_zero_to_three_ok(self):
        extract = extract_report(HOOKED_REPORT, strict=True)
        assert sum(1 for s in extract.stories if s.role == "pick") == 2
        assert validate_new_report(extract) == []

    def test_four_picks_fails_validation(self):
        extra = """
        <div class="dev-card" data-story data-story-id="pick-three" data-story-role="pick"
             data-story-topics="ai"><h3 data-story-headline>P3</h3></div>
        <div class="dev-card" data-story data-story-id="pick-four" data-story-role="pick"
             data-story-topics="ai"><h3 data-story-headline>P4</h3></div>
        """
        html = HOOKED_REPORT.replace("</div>\n  </div>\n</article>", extra + "</div>\n  </div>\n</article>")
        # Simpler: append before closing report-body
        html = HOOKED_REPORT.replace(
            'data-story-id="orphan-more"',
            'data-story-id="pick-three" data-story-role="pick" data-story-topics="ai"',
            1,
        )
        # Build a clear 4-pick fixture instead
        cards = [
            ('lead-x', 'lead', 'ai', 'Lead'),
            ('p1', 'pick', 'ai', 'P1'),
            ('p2', 'pick', 'ai', 'P2'),
            ('p3', 'pick', 'ai', 'P3'),
            ('p4', 'pick', 'ai', 'P4'),
        ]
        parts = [
            '<article class="report" data-report-date="2026-11-16" '
            'data-report-title="T" data-reading-minutes="5"><div data-report-body>'
        ]
        for sid, role, topic, headline in cards:
            parts.append(
                f'<div data-story data-story-id="{sid}" data-story-role="{role}" '
                f'data-story-topics="{topic}"><h3 data-story-headline>{headline}</h3></div>'
            )
        parts.append("</div></article>")
        extract = extract_report("".join(parts), strict=True)
        errors = validate_new_report(extract)
        assert any("pick" in e.lower() for e in errors)

    def test_does_not_manufacture_picks(self):
        html = """
        <article class="report" data-report-date="2026-11-16"
          data-report-title="T" data-reading-minutes="8">
          <div data-report-body>
            <div data-story data-story-id="only-lead" data-story-role="lead"
                 data-story-topics="ai" data-story-dek="d">
              <h3 data-story-headline>Only lead</h3>
            </div>
            <div data-story data-story-id="more-a" data-story-topics="technology">
              <h3 data-story-headline>More A</h3>
            </div>
          </div>
        </article>
        """
        extract = extract_report(html, strict=True)
        blocks = assign_homepage(extract.stories)
        assert blocks.lead is not None
        assert blocks.lead.id == "only-lead"
        assert blocks.picks == []
        assert len(blocks.more) + sum(len(v) for v in blocks.topics.values()) >= 1


class TestAssignHomepage:
    def test_priority_and_single_appearance(self):
        extract = extract_report(HOOKED_REPORT, strict=True)
        blocks = assign_homepage(extract.stories)
        assert isinstance(blocks, HomepageBlocks)
        assert blocks.lead is not None
        assert blocks.lead.id == "lead-story"
        pick_ids = [p.id for p in blocks.picks]
        assert pick_ids == ["pick-one", "pick-two"]

        seen: list[str] = [blocks.lead.id] + pick_ids
        for topic, stories in blocks.topics.items():
            assert topic in APPROVED_TOPICS
            for s in stories:
                assert s.id not in seen
                seen.append(s.id)
        for s in blocks.more:
            assert s.id not in seen
            seen.append(s.id)
        # Every story appears at most once
        all_ids = [blocks.lead.id] + pick_ids
        for stories in blocks.topics.values():
            all_ids.extend(s.id for s in stories)
        all_ids.extend(s.id for s in blocks.more)
        assert len(all_ids) == len(set(all_ids))

    def test_primary_topic_is_first_approved_slug(self):
        extract = extract_report(HOOKED_REPORT, strict=True)
        lead = next(s for s in extract.stories if s.id == "lead-story")
        assert lead.primary_topic == "ai"
        # Lead is consumed; topic-only has primary ai but lead already used ai slot story
        blocks = assign_homepage(extract.stories)
        # topic-only should land under primary topic "ai" (first approved)
        ai_ids = [s.id for s in blocks.topics.get("ai", [])]
        assert "topic-only" in ai_ids
        # Must not also appear under software-development
        soft_ids = [s.id for s in blocks.topics.get("software-development", [])]
        assert "topic-only" not in soft_ids


class TestHeadlineCapture:
    def test_span_data_story_headline_does_not_swallow_body(self):
        html = """
        <article class="report" data-report-date="2026-11-16"
          data-report-title="T" data-reading-minutes="5">
          <div data-report-body>
            <div data-story data-story-id="span-lead" data-story-role="lead"
                 data-story-topics="ai" data-story-dek="Dek only">
              <span data-story-headline>Span headline only</span>
              <p><strong>What happened:</strong> Body must not join the headline.</p>
            </div>
          </div>
        </article>
        """
        extract = extract_report(html, strict=True)
        story = extract.stories[0]
        assert story.headline == "Span headline only"
        assert "Body must not join" not in story.headline
        assert "Body must not join" in story.dek or story.dek == "Dek only"


class TestHistoricalBestEffort:
    def test_strict_false_without_lead_does_not_raise(self):
        historical = """
        <div class="container">
          <h2>🔥 Top Developments</h2>
          <div class="dev-card">
            <h3>Old card one</h3>
            <p><strong>What happened:</strong> Legacy content.</p>
          </div>
          <div class="dev-card">
            <h3>Old card two</h3>
          </div>
        </div>
        """
        extract = extract_report(historical, strict=False)
        assert isinstance(extract, ReportExtract)
        # Best-effort may yield a lead candidate from first .dev-card
        assert extract.errors == [] or isinstance(extract.errors, list)
        # Must not raise; validate_new_report may still complain but caller uses strict=False path
        blocks = assign_homepage(extract.stories)
        # Either lead from first card or empty lead → CTA fallback at render time
        assert blocks.lead is None or isinstance(blocks.lead, Story)

    def test_strict_true_missing_hooks_fails_validation(self):
        historical = """
        <div class="dev-card"><h3>No hooks</h3></div>
        """
        extract = extract_report(historical, strict=True)
        errors = validate_new_report(extract)
        assert errors
