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

Reliability notes (why this file is defensive):
  * Every LLM reply is parsed with retries, a truncation check, and a
    balanced-brace JSON extractor — a single malformed reply must not kill
    the daily cron.
  * Feeds are fetched ONCE per run with a real User-Agent, and each feed's
    entry count is logged so a dead feed is visible in the Actions log.
  * The agent refuses to publish an EMPTY brief (protects the live page),
    and emits ::error:: annotations so failures are readable in GitHub.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
from dateutil import parser as dtparse

import anthropic

from sources import FEEDS, AI_KEYWORDS, CONCEPTS

MODEL = os.environ.get("DECODER_MODEL", "claude-sonnet-4-6")
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "public" / "martech-news.json"

# Some publishers 403 the default feedparser UA; look like a normal browser.
FEED_USER_AGENT = (
    "Mozilla/5.0 (compatible; MarTechDecoder/1.1; "
    "+https://www.saurav-tripathy.com/projects/martech-ai-news)"
)

MAX_LLM_ATTEMPTS = 3   # per judge call
RETRY_BASE_SECONDS = 5


def _log(msg: str) -> None:
    print(msg, flush=True)


# ── 1. SCAN ──────────────────────────────────────────────────────────────────

def _parse_date(entry) -> datetime | None:
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                dt = dtparse.parse(val)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
    return None


def _is_ai_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in AI_KEYWORDS)


def fetch_candidates(max_days: int = 30) -> list[dict]:
    """Fetch ALL feeds once and return AI-relevant items from the last
    `max_days` days, newest first. Each item carries `_age_days` (float,
    internal only — candidates are never written to the output JSON)."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_days)
    seen: set[str] = set()
    items: list[dict] = []

    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"], agent=FEED_USER_AGENT)
        except Exception as exc:  # network hiccup on one feed must not kill the run
            _log(f"  [feed] {feed['source']}: fetch failed — {exc}")
            continue

        entries = getattr(parsed, "entries", []) or []
        if not entries:
            reason = getattr(parsed, "bozo_exception", None) or getattr(
                parsed, "status", "no entries"
            )
            _log(f"  [feed] {feed['source']}: 0 entries ({reason})")
            continue

        kept = 0
        for e in entries:
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
            kept += 1
            items.append({
                "title": title,
                "url": link,
                "source": feed["source"],
                "published": published.isoformat(),
                "summary": summary,
                "_age_days": (now - published).total_seconds() / 86400.0,
            })
        _log(f"  [feed] {feed['source']}: {len(entries)} entries, {kept} kept")

    items.sort(key=lambda x: x["_age_days"])  # newest first
    return items


def scan(days: int) -> list[dict]:
    """Back-compat helper: AI-relevant candidates from the last `days` days."""
    return fetch_candidates(days)


# ── 2. JUDGE ─────────────────────────────────────────────────────────────────

def _client() -> anthropic.Anthropic:
    # Reads ANTHROPIC_API_KEY from the environment automatically.
    return anthropic.Anthropic()


def _extract_json(text: str):
    """Parse a JSON object out of a model reply, tolerating code fences and
    stray prose. Raises ValueError with a helpful snippet if it can't."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\s*```\s*$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass

    start = t.find("{")
    if start == -1:
        raise ValueError(f"no JSON object in model reply: {t[:160]!r}…")

    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(t[start : i + 1])
    raise ValueError(
        f"unbalanced JSON in model reply (likely truncated): …{t[-160:]!r}"
    )


def _ask_json(system: str, user: str, max_tokens: int = 3000):
    """Call the model and return parsed JSON. Retries on malformed/truncated
    replies and transient API errors; fails fast on bad credentials."""
    last_err: Exception | None = None

    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            msg = _client().messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[
                    {"role": "user", "content": user},
                    # Prefill: the reply can only continue this JSON object,
                    # which eliminates prose preambles and code fences.
                    {"role": "assistant", "content": "{"},
                ],
            )
            if getattr(msg, "stop_reason", None) == "max_tokens":
                raise ValueError(f"reply truncated at max_tokens={max_tokens}")
            text = "{" + "".join(
                b.text for b in msg.content if getattr(b, "type", "") == "text"
            )
            return _extract_json(text)

        except anthropic.AuthenticationError as exc:
            raise RuntimeError(
                "Anthropic rejected the API key (401). Set/rotate the "
                "ANTHROPIC_API_KEY repo secret: Settings → Secrets and "
                f"variables → Actions. ({exc})"
            ) from exc
        except (anthropic.AnthropicError, ValueError, json.JSONDecodeError) as exc:
            last_err = exc

        if attempt < MAX_LLM_ATTEMPTS:
            wait = RETRY_BASE_SECONDS * attempt
            _log(f"  [judge] attempt {attempt} failed ({last_err}); retrying in {wait}s…")
            time.sleep(wait)
            max_tokens = int(max_tokens * 1.5)  # headroom against truncation
            user += (
                "\n\nREMINDER: reply with ONE valid, complete JSON object only — "
                "no prose, no code fences, no trailing commas."
            )

    raise RuntimeError(
        f"model returned no valid JSON after {MAX_LLM_ATTEMPTS} attempts: {last_err}"
    )


_CONCEPT_LINES = "\n".join(f'  - {cid}: {c["name"]} — {c["gloss"]}' for cid, c in CONCEPTS.items())


def _as_str_list(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, (str, int, float))]
    return []


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
    if isinstance(out, list):  # tolerate a bare top-level array
        out = {"stories": out}
    stories = [s for s in out.get("stories", []) if isinstance(s, dict)][:k]
    for i, s in enumerate(stories):
        s["num"] = f"{i+1:02d}"
        s["src"] = str(s.get("src", ""))
        s["head"] = str(s.get("head", ""))
        s["url"] = str(s.get("url", ""))
        s["plain"] = str(s.get("plain", ""))
        s["chips"] = [c for c in _as_str_list(s.get("chips")) if c in CONCEPTS][:4]
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
    out = _ask_json(system, user, max_tokens=5000)
    if isinstance(out, list):
        out = {"themes": out}
    themes = [t for t in out.get("themes", []) if isinstance(t, dict)][:k]
    for i, t in enumerate(themes):
        t["num"] = f"Theme {i+1:02d}"
        t["head"] = str(t.get("head", ""))
        t["url"] = str(t.get("url", ""))
        t["body"] = _as_str_list(t.get("body"))[:2]
        t["ev"] = [
            [str(pair[0]), str(pair[1])]
            for pair in (t.get("ev") or [])
            if isinstance(pair, (list, tuple)) and len(pair) >= 2
        ][:3]
    return {
        "skicker": str(out.get("skicker") or "30-day synthesis · the shape underneath the feed"),
        "themes": themes,
        "takeaway": str(out.get("takeaway", "")),
    }


# ── BUILD ────────────────────────────────────────────────────────────────────

def build() -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Locally: export ANTHROPIC_API_KEY=sk-ant-… ; "
            "on GitHub: repo → Settings → Secrets and variables → Actions → "
            "New repository secret → ANTHROPIC_API_KEY."
        )

    _log(f"[scan] fetching {len(FEEDS)} feeds…")
    month = fetch_candidates(30)
    week = [c for c in month if c["_age_days"] <= 7]
    day = [c for c in month if c["_age_days"] <= 1]
    _log(f"[scan] candidates — 24h: {len(day)} · 7d: {len(week)} · 30d: {len(month)}")

    if not month:
        raise RuntimeError(
            "scan produced ZERO candidates across all feeds — refusing to publish "
            "an empty brief. Check the [feed] lines above: a feed URL may have "
            "moved, or the runner may be blocked."
        )

    _log("[judge] ranking 24h window…")
    day_stories = judge_stories(day, "day", 5)
    _log("[judge] ranking 7d window…")
    week_stories = judge_stories(week, "week", 5)
    _log("[judge] synthesising 30d themes…")
    month_block = synthesize_themes(month, 5)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourcesScanned": len(FEEDS),
        "surfaced": 5,
        "concepts": CONCEPTS,
        "windows": {
            "day":   {"stories": day_stories},
            "week":  {"stories": week_stories},
            "month": month_block,
        },
    }


def main() -> None:
    try:
        data = build()
    except Exception as exc:
        msg = str(exc) or exc.__class__.__name__
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title=MarTech decoder::{msg}")
        print(f"[agent] FAILED — {msg}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    d = data["windows"]["day"]["stories"]
    m = data["windows"]["month"]["themes"]
    print(f"Wrote {OUTPUT_PATH}")
    print(f"  day: {len(d)} stories · week: {len(data['windows']['week']['stories'])} · month: {len(m)} themes")


if __name__ == "__main__":
    main()
