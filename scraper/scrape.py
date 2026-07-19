#!/usr/bin/env python3
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://career.vng.com.vn/tim-kiem-viec-lam"

FILTERS = {
    "employee_type": "Official",
    "location_city": "889",
    "job_group": "457|465|462|464",
}

DATA_FILE = Path("data/jobs.csv")
FIELDNAMES = ["job_id", "job_title", "url", "date", "last_seen", "status"]
TZ = ZoneInfo("Asia/Ho_Chi_Minh")

DETAIL_URL = BASE_URL + "/chi-tiet/{slug}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "vi,en;q=0.9",
}

def parse_next_data(html_text: str) -> dict:
    soup = BeautifulSoup(html_text, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag is None or not tag.string:
        raise ValueError("__NEXT_DATA__ script not found — page layout changed?")
    return json.loads(tag.string)


def fetch_page(page: int) -> dict:
    params = dict(FILTERS)
    if page > 1:
        params["page"] = page
    resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return parse_next_data(resp.text)["props"]["pageProps"]


def scrape_all_jobs() -> list[dict]:
    first = fetch_page(1)
    total_pages = int(first.get("pages", 1))
    jobs = list(first.get("jobs", []))

    for page in range(2, total_pages + 1):
        time.sleep(1)
        jobs.extend(fetch_page(page).get("jobs", []))

    seen, unique = set(), []
    for jb in jobs:
        jid = str(jb.get("job_id"))
        if jid and jid not in seen:
            seen.add(jid)
            slug = (jb.get("slug") or "").strip()
            unique.append({
                "job_id": jid,
                "job_title": (jb.get("title") or "").strip(),
                "url": DETAIL_URL.format(slug=slug) if slug else "",
            })
    return unique


def load_existing() -> dict[str, dict]:
    if not DATA_FILE.exists():
        return {}
    with DATA_FILE.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return {}
        has_id = "job_id" in reader.fieldnames
        records: dict[str, dict] = {}
        for row in reader:
            title = (row.get("job_title") or "").strip()
            date = (row.get("date") or "").strip()
            url = (row.get("url") or "").strip()
            last_seen = (row.get("last_seen") or date).strip()
            status = (row.get("status") or "open").strip()
            jid = (row.get("job_id") or "").strip() if has_id else ""
            key = jid or title
            if not key:
                continue
            records[key] = {"job_id": jid, "job_title": title, "url": url,
                            "date": date, "last_seen": last_seen, "status": status}
    return records


def save(records: dict[str, dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(records.values(), key=lambda r: (r["date"], r["job_id"]))
    with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    scraped = scrape_all_jobs()

    if not scraped:
        print("No jobs parsed — aborting so we don't wipe existing data.")
        return 1

    existing = load_existing()
    seen_ids = set()
    new_count = 0
    for job in scraped:
        jid, title, url = job["job_id"], job["job_title"], job["url"]
        seen_ids.add(jid)
        if jid in existing:
            existing[jid].update(job_id=jid, job_title=title, url=url,
                                 last_seen=today, status="open")
        elif title in existing:
            rec = existing.pop(title)
            rec.update(job_id=jid, url=url, last_seen=today, status="open")
            existing[jid] = rec
        else:
            existing[jid] = {**job, "date": today, "last_seen": today,
                             "status": "open"}
            new_count += 1

    closed_count = 0
    for rec in existing.values():
        if rec.get("job_id") not in seen_ids and rec.get("status") != "closed":
            rec["status"] = "closed"
            closed_count += 1

    save(existing)
    print(f"Scraped {len(scraped)} jobs. "
          f"New: {new_count} ({today}). Newly closed: {closed_count}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
