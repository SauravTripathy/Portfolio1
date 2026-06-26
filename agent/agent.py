#!/usr/bin/env python3
"""
MarTech AI — the Decoder's Brief : agent
========================================

Two-step agent:
  1) SCAN   — pull candidate articles from RSS feeds, filter to AI-relevant and
              to each time window (24h / 7d / 30d).
  2) JUDGE  — an LLM ranks the candidates and produces the top 5 per window,
              each decoded into plain English and tagged with concepts.
              For the month window it instead synthesises the top 5 themes.

Output: ../public/martech-news.json  (the page reads this exact file).

Run:
    export ANTHROPIC_API_KEY=sk-ant-...     # <-- the only key you must set
    python agent/agent.py

Optional env:
    DECODER_MODEL   (default: claude-sonnet-4-6)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
from dateutil import parser as dtparse

import anthropic

from sources import FEEDS, AI_KEYWORDS, CONCEPTS

MODEL = os.environ.get("DECODER_MODEL", "claude-sonnet-4-6")
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "public" / "martech-news.json"


# ── 1. SCAN ──────────────────────────────────────────────────────────────────

def _parse_date(entry) -> datetime | None:
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                dt = dtparse.parse(val)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
    return None


def _is_ai_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in AI_KEYWORDS)


def scan(days: int) -> list[dict]:
    """Return AI-relevant candidate articles published within `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    seen: set[str] = set()
    items: list[dict] = []

    for feed in FEEDS:
        parsed = feedparser.parse(feed["url"])
        for e in parsed.entries:
            published = _parse_date(e)
            if published is None or published < cutoff:
                continue
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = re.sub(r"<[^>]+>", "", e.get("summary", ""))[:600].strip()
            if not title or not link:
                continue
            if not _is_ai_relevant(f"{title} {summary}"):
                continue
            key = link or title.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "title": title,
                "url": link,
                "source": feed["source"],
                "published": published.isoformat(),
                "summary": summary,
            })

    items.sort(key=lambda x: x["published"], reverse=True)
    return items


# ── 2. JUDGE ─────────────────────────────────────────────────────────────────

def _client() -> anthropic.Anthropic:
    # Reads ANTHROPIC_API_KEY from the environment automatically.
    return anthropic.Anthropic()


def _ask_json(system: str, user: str, max_tokens: int = 3000):
    """Call the model and parse a JSON-only reply (tolerates code fences)."""
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


_CONCEPT_LINES = "\n".join(f'  - {cid}: {c["name"]} — {c["gloss"]}' for cid, c in CONCEPTS.items())


def judge_stories(candidates: list[dict], window: str, k: int = 5) -> list[dict]:
    """Rank candidates and return the top k decoded stories."""
    if not candidates:
        return []

    pool = candidates[:40]
    listing = "\n".join(
        f'[{i}] {c["source"]} | {c["published"][:10]} | {c["title"]}\n     {c["summary"]}\n     URL: {c["url"]}'
        for i, c in enumerate(pool)
    )
    horizon = "the last 24 hours" if window == "day" else "the past 7 days"
    today = datetime.now(timezone.utc).date().isoformat()

    system = (
        "You are an editor for a MarTech-AI onboarding brief read by people new to the field. "
        "You rank news by what changes how marketing AI is bought, built, or governed — not by recency alone. "
        "You write plain English a smart non-specialist can follow (≈grade 8). Reply with JSON only."
    )
    user = f"""Today is {today}. From the candidate articles below (covering {horizon}), pick the {k} most newsworthy.

Reject logo-deal partnerships with no product change, award round-ups, and vendor superlatives with no substance.

For each chosen article return an object:
  "num":   two-digit rank string, "01".."{k:02d}"
  "src":   short source label (you may append "· via <Source>")
  "fresh": true only if published within the last 24 hours of {today}
  "head":  the article headline (concise, factual)
  "url":   the article URL, copied exactly from the candidate
  "plain": 40–70 words of plain English explaining what it is and why it matters; you may wrap 1–2 key phrases in <b>…</b>
  "chips": 2–4 concept ids the reader needs, chosen ONLY from this taxonomy:
{_CONCEPT_LINES}

Return JSON: {{ "stories": [ ... {k} objects ... ] }}  — no prose, no code fences.

Candidates:
{listing}
"""
    out = _ask_json(system, user, max_tokens=3500)
    stories = out.get("stories", [])[:k]
    for i, s in enumerate(stories):
        s["num"] = f"{i+1:02d}"
        s["chips"] = [c for c in s.get("chips", []) if c in CONCEPTS][:4]
        s["fresh"] = bool(s.get("fresh"))
    return stories


def synthesize_themes(candidates: list[dict], k: int = 5) -> dict:
    """Cluster the month's candidates into the top k themes."""
    if not candidates:
        return {"skicker": "30-day synthesis · the shape underneath the feed", "themes": [], "takeaway": ""}

    pool = candidates[:60]
    listing = "\n".join(
        f'- {c["source"]} | {c["published"][:10]} | {c["title"]} | {c["url"]}'
        for c in pool
    )
    system = (
        "You are a strategy editor synthesising a month of MarTech-AI news for someone new to the field. "
        "You group items into underlying shifts that change a decision — not lists of headlines. Reply with JSON only."
    )
    user = f"""From the past-30-days items below, produce the {k} most important THEMES.

For each theme return an object:
  "num":  "Theme 01".."Theme {k:02d}"
  "head": a sharp theme title; wrap the 1–3 most evocative words in <em>…</em>
  "url":  the single best primary-source URL for the theme, copied from an item below
  "body": array of EXACTLY 2 short paragraphs (≈2–3 sentences each) in plain English; you may use <b>…</b> for emphasis; if you write an ampersand inside text, write it as &amp;
  "ev":   array of 2–3 [label, url] pairs citing items below (label like "Source · short")

Also return:
  "takeaway": one sentence framing the whole landscape; wrap the key clause in <em>…</em>
  "skicker":  "30-day synthesis · the shape underneath the feed"

Return JSON: {{ "skicker": "...", "themes": [ ... {k} ... ], "takeaway": "..." }} — no prose, no code fences.

Items:
{listing}
"""
    out = _ask_json(system, user, max_tokens=4000)
    themes = out.get("themes", [])[:k]
    for i, t in enumerate(themes):
        t["num"] = f"Theme {i+1:02d}"
    return {
        "skicker": out.get("skicker", "30-day synthesis · the shape underneath the feed"),
        "themes": themes,
        "takeaway": out.get("takeaway", ""),
    }


# ── BUILD ────────────────────────────────────────────────────────────────────

def build() -> dict:
    day = scan(1)
    week = scan(7)
    month = scan(30)

    data = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourcesScanned": len(FEEDS),
        "surfaced": 5,
        "concepts": CONCEPTS,
        "windows": {
            "day":   {"stories": judge_stories(day, "day", 5)},
            "week":  {"stories": judge_stories(week, "week", 5)},
            "month": synthesize_themes(month, 5),
        },
    }
    return data


def main() -> None:
    data = build()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    d = data["windows"]["day"]["stories"]
    m = data["windows"]["month"]["themes"]
    print(f"Wrote {OUTPUT_PATH}")
    print(f"  day: {len(d)} stories · week: {len(data['windows']['week']['stories'])} · month: {len(m)} themes")


if __name__ == "__main__":
    main()
