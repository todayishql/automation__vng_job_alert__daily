#!/usr/bin/env python3
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

DATA_FILE = Path("data/jobs.csv")
IMAGE = Path("data/leaderboard.png")
TZ = ZoneInfo("Asia/Ho_Chi_Minh")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API = f"https://api.telegram.org/bot{TOKEN}"


def esc(s: str) -> str:
    """Escape for Telegram parse_mode=HTML."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def new_jobs(today: str) -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open(newline="", encoding="utf-8") as f:
        return [
            r for r in csv.DictReader(f)
            if (r.get("date") == today) and ((r.get("status") or "open") == "open")
        ]


def send_message(text: str) -> None:
    resp = requests.post(
        f"{API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": "true"},
        timeout=30,
    )
    resp.raise_for_status()


def send_photo(path: Path, caption: str) -> None:
    with open(path, "rb") as img:
        resp = requests.post(
            f"{API}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": img},
            timeout=60,
        )
    resp.raise_for_status()


def build_message(jobs: list[dict], today: str) -> str:
    lines = [f"<b>{len(jobs)} job mới tại VNG</b> ({today})", ""]
    for j in jobs:
        title = esc(j.get("job_title", ""))
        url = j.get("url", "")
        lines.append(f'• <a href="{url}">{title}</a>' if url else f"• {title}")
    return "\n".join(lines)


def main() -> int:
    if not TOKEN or not CHAT_ID:
        print("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID — skipping.")
        return 0 

    today = datetime.now(TZ).strftime("%Y-%m-%d")
    jobs = new_jobs(today)
    if not jobs:
        print("No new jobs today — no Telegram alert sent.")
        return 0

    send_message(build_message(jobs, today))
    if IMAGE.exists():
        send_photo(IMAGE, f"VNG Data Jobs - Leaderboard ({today})")
    print(f"Sent Telegram alert for {len(jobs)} new job(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
