#!/usr/bin/env python3
"""
Optional live API for the Refresh button.

By default the page's Refresh button just re-fetches the latest committed
martech-news.json. If you'd rather have Refresh RUN THE AGENT LIVE, deploy this
small server (e.g. to a Hugging Face Space, like your other agents) and paste its
URL into REFRESH_ENDPOINT in martech-ai-news.astro.

Run locally:
    export ANTHROPIC_API_KEY=sk-ant-...
    uvicorn server:app --reload --port 8000
    # then set REFRESH_ENDPOINT = "http://localhost:8000/refresh"

Note: each call runs the full scan+judge (LLM calls), so results are cached for
CACHE_TTL seconds to avoid hammering the API on repeated clicks.
"""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent import build

app = FastAPI(title="MarTech AI Decoder")

# Restrict to your own site in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://saurav-tripathy.com",
        "https://www.saurav-tripathy.com",
        "http://localhost:4321",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

CACHE_TTL = 600  # seconds
_cache: dict = {"at": 0.0, "data": None}


def _run():
    now = time.time()
    if _cache["data"] is None or now - _cache["at"] > CACHE_TTL:
        _cache["data"] = build()
        _cache["at"] = now
    return _cache["data"]


@app.get("/refresh")
@app.post("/refresh")
def refresh():
    return _run()


@app.get("/health")
def health():
    return {"ok": True}
