"""Contract test verifying prompts/daily-report.md matches codebase expectations."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "prompts" / "daily-report.md"


def get_prompt_text() -> str:
    assert PROMPT_PATH.is_file(), f"Prompt file not found at {PROMPT_PATH}"
    return PROMPT_PATH.read_text(encoding="utf-8")


def test_section_headings_match():
    """Every section heading expected by wrap_report.py must appear in Part 5 list."""
    prompt = get_prompt_text()
    expected_headings = [
        "🔥 Top Developments",
        "🧠 Emerging AI Trends",
        "💻 Developer & Coding AI",
        "🧩 Agentic AI Watch",
        "🔐 AI Security Watch",
        "📚 Research Worth Reading",
        "🚀 What to Watch Next",
        "🎯 Bottom Line",
    ]
    # Part 5 lists items like: 1. `🔥 Top Developments`
    for heading in expected_headings:
        pattern = rf"`{re.escape(heading)}`"
        assert re.search(pattern, prompt), f"Expected heading `{heading}` not found in prompt Part 5"


def test_no_email_addresses():
    """Prompt file must contain no email addresses."""
    prompt = get_prompt_text()
    # RFC 5322 simplified email regex
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    matches = re.findall(email_pattern, prompt)
    assert not matches, f"Found email addresses in prompt file: {matches}"


def test_no_first_person_or_forbidden_phrases():
    """Prompt file must not contain 'Personally' or 'What I Would'."""
    prompt = get_prompt_text()
    assert "Personally" not in prompt, "Found 'Personally' in prompt file"
    assert "What I Would" not in prompt, "Found 'What I Would' in prompt file"


def test_part7_commands_match_argparse_flags():
    """Commands in Part 7 must only use flags that publish_report.py and send_intelligence_email.py define."""
    prompt = get_prompt_text()

    # Check publish_report.py invocation in Part 7
    # Defined flags in publish_report.py: --date, --html, --description
    publish_flags = ["--date", "--html", "--description"]
    # Look for command block with publish_report.py
    pub_match = re.search(r"publish_report\.py\s*\\?\n((?:\s*--[a-z-]+\s+[^\n]+\s*\\?\n?)+)", prompt)
    assert pub_match, "Could not locate publish_report.py command block in prompt Part 7"
    called_flags = re.findall(r"(--[a-z-]+)", pub_match.group(1))
    for flag in called_flags:
        assert flag in publish_flags, f"Unknown flag {flag} in publish_report.py command in Part 7"

    # Check send_intelligence_email.py invocation in Part 7
    # Defined flags: --subject, --html, --link-only, --date, --pr-url
    email_flags = ["--subject", "--html", "--link-only", "--date", "--pr-url"]
    email_match = re.search(r"send_intelligence_email\.py\s*\\?\n((?:\s*--[a-z-]+\s*[^\n]*\s*\\?\n?)+)", prompt)
    assert email_match, "Could not locate send_intelligence_email.py command block in prompt Part 7"
    called_email_flags = re.findall(r"(--[a-z-]+)", email_match.group(1))
    for flag in called_email_flags:
        assert flag in email_flags, f"Unknown flag {flag} in send_intelligence_email.py command in Part 7"


def test_no_hardcoded_emails_in_scripts_and_workflows():
    """Scripts and .github/ workflows must not contain email addresses except the GitHub Actions bot."""
    allowed = {"41898282+github-actions[bot]@users.noreply.github.com"}
    # Require standard email format with letters for domain and TLD (2+ chars)
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}'

    scan_dirs = [REPO_ROOT / "scripts", REPO_ROOT / ".github"]
    violations = []
    for sdir in scan_dirs:
        for p in sdir.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".yml", ".yaml", ".sh"):
                text = p.read_text(encoding="utf-8")
                found = set(re.findall(email_pattern, text))
                bad = found - allowed
                if bad:
                    violations.append(f"{p.relative_to(REPO_ROOT)}: {bad}")
    assert not violations, f"Found unauthorized email addresses: {violations}"


def test_report_skeleton_contract():
    """Report skeleton must process cleanly through wrapper and satisfy contract."""
    from datetime import datetime
    import sys
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from wrap_report import prepare_report_body, build_report_page

    skeleton_path = REPO_ROOT / "prompts" / "report-skeleton.html"
    assert skeleton_path.is_file(), "Skeleton file missing at prompts/report-skeleton.html"
    raw_skeleton = skeleton_path.read_text(encoding="utf-8")

    processed_body = prepare_report_body(raw_skeleton)
    full_page = build_report_page(datetime(2026, 9, 21), "Sample Description", processed_body)

    expected_ids = [
        "top-developments",
        "emerging-trends",
        "developer-coding",
        "agentic-watch",
        "security-watch",
        "research",
        "watch-next",
        "bottom-line",
    ]
    # Assert all 8 anchor ids are present
    for aid in expected_ids:
        assert f'id="{aid}"' in full_page, f"Anchor id '{aid}' missing in generated page"

    # Assert TOC hrefs match ids that exist in the page
    toc_hrefs = re.findall(r'<a href="#([^"]+)">', full_page)
    assert set(expected_ids).issubset(set(toc_hrefs)), f"TOC hrefs {toc_hrefs} do not contain all expected ids {expected_ids}"
    for href in toc_hrefs:
        assert f'id="{href}"' in full_page, f"TOC target id '{href}' does not exist in the page"

    # Assert stars become accessible "out of 5" markup
    assert '<span class="visually-hidden">Impact: 5 out of 5</span>' in full_page
    assert '<span aria-hidden="true">⭐⭐⭐⭐⭐</span>' in full_page

    # Assert takeaway and dev-card classes survive
    assert 'class="takeaway"' in full_page
    assert 'class="dev-card"' in full_page
    assert 'class="security-item"' in full_page
    assert 'class="bottom-line"' in full_page


def test_prompt_mentions_skeleton():
    """Prompt must explicitly instruct copying from prompts/report-skeleton.html."""
    prompt = get_prompt_text()
    assert "prompts/report-skeleton.html" in prompt, "Prompt does not mention prompts/report-skeleton.html"

