#!/usr/bin/env python3
"""Render a top-20 job leaderboard PNG from data/jobs.csv."""

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

DATA_FILE = Path("data/jobs.csv")
OUT = Path("data/leaderboard.png")
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
TOP = 20

BG, CARD, CARD_1 = "#0d1117", "#161b22", "#1c2330"
TEXT, MUTED, RANKCLR = "#e6edf3", "#8b949e", "#f0883e"
BADGE = {
    "new":    ("#1a7f37", "#ffffff", "NEW"),
    "recent": ("#2d333b", "#adbac7", None),
    "old":    ("#21262d", "#768390", None),
    "closed": ("#3d1418", "#f85149", "closed"),
}


def load():
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def recency(rec, today):
    if (rec.get("status") or "open") == "closed":
        return "closed", "closed"
    d = datetime.strptime(rec["date"], "%Y-%m-%d").date()
    n = (today - d).days
    if n <= 0:
        return "NEW", "new"
    if n == 1:
        return "1 day ago", "recent"
    return f"{n} days ago", "recent" if n <= 7 else "old"


def sort_key(rec):
    is_open = (rec.get("status") or "open") == "open"
    ref = rec.get("date") if is_open else (rec.get("last_seen") or rec.get("date") or "0000-01-01")
    ordv = datetime.strptime(ref, "%Y-%m-%d").date().toordinal()
    return (0 if is_open else 1, -ordv)


def truncate(s, n=50):
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    today = datetime.now(TZ).date()
    rows = sorted(load(), key=sort_key)[:TOP]
    if not rows:
        print("No data to render.")
        return

    n = len(rows)
    row_h = 0.62
    fig_h = 1.7 + n * row_h
    fig, ax = plt.subplots(figsize=(9.2, fig_h), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    ax.text(2.5, fig_h - 0.55, "VNG Data Jobs — Leaderboard",
            color=TEXT, fontsize=17, fontweight="bold", va="center")
    ax.text(2.5, fig_h - 1.05,
            f"Top {n} · updated {today:%Y-%m-%d} (Asia/Ho_Chi_Minh)",
            color=MUTED, fontsize=9.5, va="center")

    y = fig_h - 1.7
    for i, rec in enumerate(rows, 1):
        label, kind = recency(rec, today)
        bg = CARD_1 if i <= 3 else CARD
        ax.add_patch(FancyBboxPatch(
            (2.5, y - row_h * 0.5 + 0.06), 95, row_h - 0.14,
            boxstyle="round,pad=0.02,rounding_size=0.15",
            linewidth=0, facecolor=bg, mutation_aspect=0.06))
        ax.text(6.5, y, f"#{i}", color=RANKCLR if i <= 3 else MUTED,
                fontsize=12.5, fontweight="bold", va="center", ha="center")
        closed = kind == "closed"
        ax.text(12, y, truncate(rec.get("job_title", "")),
                color=(MUTED if closed else TEXT), fontsize=11, va="center",
                alpha=0.65 if closed else 1.0)
        fill, fg, forced = BADGE[kind]
        txt = forced or label
        bx, bw = 78.5, 18.5
        ax.add_patch(FancyBboxPatch(
            (bx, y - 0.19), bw, 0.38,
            boxstyle="round,pad=0.02,rounding_size=0.19",
            linewidth=0, facecolor=fill, mutation_aspect=0.5))
        ax.text(bx + bw / 2, y, txt, color=fg, fontsize=9,
                fontweight="bold" if forced else "normal", va="center", ha="center")
        y -= row_h

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    print(f"Wrote {OUT} ({n} rows).")


if __name__ == "__main__":
    main()
