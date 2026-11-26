"""Optional: push today's headlines to your phone via a Telegram bot.

Set TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID and PAGE_URL (GitHub secrets). Does nothing otherwise.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests


def format_message(summary: dict, page_url: str, limit: int = 8) -> str:
    lines = [f"AI + QA Radar: {summary['new_today']} new today"]
    if summary.get("failures"):
        lines.append(f"⚠ {len(summary['failures'])} source(s) failed")
    lines += [f"• {title}" for title in summary.get("headlines", [])[:limit]]
    if page_url:
        lines.append(page_url)
    return "\n".join(lines)


def send_telegram(summary: dict, now: datetime | None = None) -> bool:
    """The collector runs every 30 min; only the run in NOTIFY_HOUR_UTC (default 02) messages you."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    now = now or datetime.now(timezone.utc)
    hour = int(os.environ.get("NOTIFY_HOUR_UTC") or 2)
    if not token or not chat or not summary.get("new_today") or now.hour != hour or now.minute >= 30:
        return False
    text = format_message(summary, os.environ.get("PAGE_URL", ""))
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
                      timeout=20).raise_for_status()
        return True
    except requests.RequestException:
        return False  # a failed notification must never fail the build
