#!/usr/bin/env python3
"""Send AI Daily Intelligence HTML report via SMTP using environment secrets."""

from __future__ import annotations

import argparse
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def parse_recipients(raw: str) -> list[str]:
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Send AI Daily Intelligence report via SMTP")
    parser.add_argument("--html", required=True, help="Path to HTML email body")
    parser.add_argument("--subject", required=True, help="Email subject line")
    args = parser.parse_args()

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
        return 1

    with open(args.html, "r", encoding="utf-8") as handle:
        html = handle.read()

    message = MIMEMultipart("alternative")
    message["Subject"] = args.subject
    message["From"] = user
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL(host, port, timeout=30) as server:
        server.login(user, password)
        server.sendmail(user, recipients, message.as_string())

    print(f"Email sent to: {', '.join(recipients)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
