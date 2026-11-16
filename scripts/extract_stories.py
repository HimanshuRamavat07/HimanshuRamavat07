"""Parse daily report HTML into homepage/archive story metadata.

Design contract: docs editorial redesign §5. Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from typing import Iterable

APPROVED_TOPICS: tuple[str, ...] = (
    "ai",
    "software-development",
    "startups",
    "technology",
)

TOPIC_LABELS: dict[str, str] = {
    "ai": "AI",
    "software-development": "Software & Development",
    "startups": "Startups",
    "technology": "Technology",
}

SUPPORTED_ROLES = frozenset({"lead", "pick", "more"})

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class Story:
    id: str
    role: str | None
    topics: list[str]
    headline: str
    dek: str
    primary_topic: str | None


@dataclass
class HomepageBlocks:
    lead: Story | None
    picks: list[Story]
    topics: dict[str, list[Story]]
    more: list[Story]


@dataclass
class ReportExtract:
    date: str | None
    title: str | None
    reading_minutes: int | None
    stories: list[Story]
    errors: list[str] = field(default_factory=list)


def _norm_space(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text or "").strip()


def _filter_topics(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for part in raw.split(","):
        slug = part.strip().lower()
        if not slug:
            continue
        if slug in APPROVED_TOPICS and slug not in out:
            out.append(slug)
        # Unknown slugs: silently ignore (design §5.2 / §5.3)
    return out


def _primary_topic(topics: Iterable[str]) -> str | None:
    for slug in topics:
        if slug in APPROVED_TOPICS:
            return slug
    return None


class _StoryAwareParser(HTMLParser):
    """Track element depth so data-story blocks close correctly."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.report_attrs: dict[str, str] = {}
        self.raw_stories: list[dict] = []
        self.legacy_cards: list[dict] = []
        self._story: dict | None = None
        self._story_depth = 0
        self._capture_headline = False
        self._legacy: dict | None = None
        self._legacy_depth = 0
        self._capture_legacy_h3 = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}

        if self._story is not None:
            self._story_depth += 1
            if self._capture_headline:
                return
            if tag == "h3" or "data-story-headline" in ad:
                self._capture_headline = True
                self._story["_hchunks"] = []
            return

        if self._legacy is not None:
            self._legacy_depth += 1
            if tag == "h3" and not self._legacy.get("headline"):
                self._capture_legacy_h3 = True
                self._legacy["_hchunks"] = []
            return

        if tag == "article" or "data-report-date" in ad:
            for key in ("data-report-date", "data-report-title", "data-reading-minutes"):
                if key in ad and ad[key]:
                    self.report_attrs[key] = ad[key]

        if "data-story" in ad:
            self._story = {
                "id": (ad.get("data-story-id") or "").strip(),
                "role": (ad.get("data-story-role") or "").strip() or None,
                "topics_raw": ad.get("data-story-topics") or "",
                "dek": _norm_space(ad.get("data-story-dek") or ""),
                "headline": "",
                "body_text": "",
                "_hchunks": [],
                "_tchunks": [],
            }
            self._story_depth = 1
            return

        classes = (ad.get("class") or "").split()
        if tag == "div" and "dev-card" in classes:
            self._legacy = {
                "headline": "",
                "body_text": "",
                "_hchunks": [],
                "_tchunks": [],
            }
            self._legacy_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self._story is not None:
            if self._capture_headline and tag in ("h3", "span", "a", "strong", "em"):
                if tag == "h3":
                    self._story["headline"] = _norm_space("".join(self._story.get("_hchunks", [])))
                    self._capture_headline = False
            self._story_depth -= 1
            if self._story_depth <= 0:
                self._story["body_text"] = _norm_space("".join(self._story.get("_tchunks", [])))
                self.raw_stories.append(self._story)
                self._story = None
                self._capture_headline = False
            return

        if self._legacy is not None:
            if self._capture_legacy_h3 and tag == "h3":
                self._legacy["headline"] = _norm_space("".join(self._legacy.get("_hchunks", [])))
                self._capture_legacy_h3 = False
            self._legacy_depth -= 1
            if self._legacy_depth <= 0:
                self._legacy["body_text"] = _norm_space("".join(self._legacy.get("_tchunks", [])))
                if self._legacy.get("headline"):
                    self.legacy_cards.append(
                        {
                            "headline": self._legacy["headline"],
                            "body_text": self._legacy["body_text"],
                        }
                    )
                self._legacy = None
                self._capture_legacy_h3 = False

    def handle_data(self, data: str) -> None:
        if self._story is not None:
            if self._capture_headline:
                self._story.setdefault("_hchunks", []).append(data)
            else:
                self._story.setdefault("_tchunks", []).append(data)
        elif self._legacy is not None:
            if self._capture_legacy_h3:
                self._legacy.setdefault("_hchunks", []).append(data)
            else:
                self._legacy.setdefault("_tchunks", []).append(data)


def _dek_from_body(body: str, explicit: str) -> str:
    if explicit:
        return explicit
    # Prefer "What happened:" paragraph text
    match = re.search(
        r"What happened:\s*(.+?)(?:Why it matters:|$)",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return _norm_space(match.group(1))
    return _norm_space(body)[:240]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "story"


def extract_report(html: str, *, strict: bool) -> ReportExtract:
    parser = _StoryAwareParser()
    parser.feed(html or "")
    parser.close()

    errors: list[str] = []
    date = parser.report_attrs.get("data-report-date")
    title = _norm_space(parser.report_attrs.get("data-report-title") or "") or None
    minutes_raw = parser.report_attrs.get("data-reading-minutes")
    reading_minutes: int | None = None

    if date:
        if not ISO_DATE_RE.match(date):
            errors.append(f"Invalid report date (expected YYYY-MM-DD): {date}")
            date = None
        else:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Invalid report date: {date}")
                date = None
    elif strict:
        errors.append("Missing data-report-date")

    if minutes_raw is not None and minutes_raw != "":
        try:
            reading_minutes = int(minutes_raw)
            if reading_minutes <= 0:
                errors.append("data-reading-minutes must be a positive integer")
                reading_minutes = None
        except ValueError:
            errors.append("data-reading-minutes must be a positive integer")
    elif strict:
        errors.append("Missing data-reading-minutes")

    if strict and not title:
        errors.append("Missing data-report-title")

    stories: list[Story] = []
    seen_ids: set[str] = set()

    for raw in parser.raw_stories:
        sid = raw["id"] or _slugify(raw.get("headline") or "story")
        if sid in seen_ids:
            errors.append(f"Duplicate story id: {sid}")
            continue
        seen_ids.add(sid)

        role = raw.get("role")
        if role is not None and role not in SUPPORTED_ROLES:
            errors.append(f"Invalid story role for {sid}: {role}")
            role = None

        topics = _filter_topics(raw.get("topics_raw"))
        headline = _norm_space(raw.get("headline") or "")
        if not headline:
            errors.append(f"Missing headline for story {sid}")
            continue
        dek = _dek_from_body(raw.get("body_text") or "", raw.get("dek") or "")
        stories.append(
            Story(
                id=sid,
                role=role,
                topics=topics,
                headline=headline,
                dek=dek,
                primary_topic=_primary_topic(topics),
            )
        )

    # Historical best-effort when no data-story hooks
    if not stories and parser.legacy_cards and not strict:
        for idx, card in enumerate(parser.legacy_cards):
            sid = _slugify(card["headline"])
            if sid in seen_ids:
                sid = f"{sid}-{idx}"
            seen_ids.add(sid)
            role = "lead" if idx == 0 else "more"
            dek = _dek_from_body(card.get("body_text") or "", "")
            stories.append(
                Story(
                    id=sid,
                    role=role,
                    topics=[],
                    headline=card["headline"],
                    dek=dek,
                    primary_topic=None,
                )
            )

    return ReportExtract(
        date=date,
        title=title,
        reading_minutes=reading_minutes,
        stories=stories,
        errors=errors,
    )


def assign_homepage(stories: list[Story]) -> HomepageBlocks:
    """Placement priority: lead → picks → topics → more; one appearance each."""
    used: set[str] = set()
    lead: Story | None = None
    for story in stories:
        if story.role == "lead":
            lead = story
            used.add(story.id)
            break

    picks: list[Story] = []
    for story in stories:
        if story.id in used:
            continue
        if story.role == "pick":
            if len(picks) >= 3:
                break
            picks.append(story)
            used.add(story.id)

    topics: dict[str, list[Story]] = {slug: [] for slug in APPROVED_TOPICS}
    for story in stories:
        if story.id in used:
            continue
        primary = story.primary_topic
        if primary:
            topics[primary].append(story)
            used.add(story.id)

    # Drop empty topic keys for callers that iterate .items(); keep dict with only non-empty
    topics = {k: v for k, v in topics.items() if v}

    more: list[Story] = []
    for story in stories:
        if story.id in used:
            continue
        more.append(story)
        used.add(story.id)

    return HomepageBlocks(lead=lead, picks=picks, topics=topics, more=more)


def validate_new_report(extract: ReportExtract) -> list[str]:
    """Return non-empty list ⇒ fail publish for new reports."""
    errors = list(extract.errors)
    leads = [s for s in extract.stories if s.role == "lead"]
    if len(leads) != 1:
        errors.append(f"New reports require exactly one lead story (found {len(leads)})")
    picks = [s for s in extract.stories if s.role == "pick"]
    if len(picks) > 3:
        errors.append(f"Editor's picks must be 0–3 (found {len(picks)})")
    if not extract.date:
        errors.append("New reports require data-report-date")
    if not extract.title:
        errors.append("New reports require data-report-title")
    if extract.reading_minutes is None or extract.reading_minutes <= 0:
        errors.append("New reports require positive data-reading-minutes")
    ids = [s.id for s in extract.stories]
    if len(ids) != len(set(ids)):
        errors.append("Story ids must be unique within the report")
    return errors
