#!/usr/bin/env python3
"""Send AI Daily Intelligence notifications via SMTP using environment secrets."""

from __future__ import annotations

import argparse
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PAGES_BASE = "https://himanshuramavat07.github.io/HimanshuRamavat07"


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def parse_recipients(raw: str) -> list[str]:
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def send_message(subject: str, html_body: str, text_body: str) -> None:
    host = required_env("SMTP_HOST")
    port = int(required_env("SMTP_PORT"))
    user = required_env("SMTP_USER")
    password = required_env("SMTP_PASS")
    recipients = parse_recipients(
        os.environ.get(
            "SMTP_RECIPIENTS",
            "himanshu.ramavat@mail.nitsan.ai,hr20072001@gmail.com",
        )
    )
    if not recipients:
        print("ERROR: No recipients configured", file=sys.stderr)
        sys.exit(1)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = user
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(host, port, timeout=30) as server:
        server.login(user, password)
        server.sendmail(user, recipients, message.as_string())

    print(f"Email sent to: {', '.join(recipients)}")


def build_link_notification(date: str, pr_url: str | None) -> tuple[str, str]:
    report_url = f"{PAGES_BASE}/reports/{date}.html"
    index_url = f"{PAGES_BASE}/"
    pr_line_html = f'<p><strong>Review PR:</strong> <a href="{pr_url}">{pr_url}</a></p>' if pr_url else ""
    pr_line_text = f"Review PR: {pr_url}\n\n" if pr_url else ""

    text_body = (
        f"Hi,\n\n"
        f"Today's AI Daily Intelligence briefing for {date} is ready.\n\n"
        f"{pr_line_text}"
        f"After you merge the PR, the report will be published here:\n"
        f"{report_url}\n\n"
        f"Archive:\n{index_url}\n\n"
        f"Best regards,\nAI Intelligence Automation"
    )
    html_body = f"""<!DOCTYPE html>
<html lang="en"><body style="font-family: sans-serif; line-height: 1.6; color: #111;">
<p>Hi,</p>
<p>Today's <strong>AI Daily Intelligence</strong> briefing for <strong>{date}</strong> is ready.</p>
{pr_line_html}
<p>After you merge the PR, the report will be published here:</p>
<p><a href="{report_url}">{report_url}</a></p>
<p>Archive: <a href="{index_url}">{index_url}</a></p>
<p>Best regards,<br><strong>AI Intelligence Automation</strong></p>
</body></html>"""
    return text_body, html_body


def main() -> int:
    parser = argparse.ArgumentParser(description="Send AI Daily Intelligence email notifications")
    parser.add_argument("--subject", help="Email subject line")
    parser.add_argument("--html", help="Path to full HTML report body")
    parser.add_argument(
        "--link-only",
        action="store_true",
        help="Send a short notification with GitHub Pages and PR links instead of the full report",
    )
    parser.add_argument("--date", help="Report date in YYYY-MM-DD format (required with --link-only)")
    parser.add_argument("--pr-url", help="Pull request URL to include in link-only notifications")
    args = parser.parse_args()

    if args.link_only:
        if not args.date:
            print("ERROR: --date is required with --link-only", file=sys.stderr)
            return 1
        subject = args.subject or f"🤖 AI Daily Intelligence — {args.date} (ready for review)"
        text_body, html_body = build_link_notification(args.date, args.pr_url)
        send_message(subject, html_body, text_body)
        return 0

    if not args.html or not args.subject:
        print("ERROR: --html and --subject are required unless using --link-only", file=sys.stderr)
        return 1

    html_path = Path(args.html)
    if not html_path.is_file():
        print(f"ERROR: HTML file not found: {html_path}", file=sys.stderr)
        return 1

    html_body = html_path.read_text(encoding="utf-8")
    text_body = "Today's AI Daily Intelligence report is attached as HTML."
    send_message(args.subject, html_body, text_body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
