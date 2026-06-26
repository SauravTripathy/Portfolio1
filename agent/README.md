# MarTech AI — Decoder's Brief agent

A two-step agent that feeds `src/pages/projects/martech-ai-news.astro`.

1. **Scan** — pull candidate articles from the RSS feeds in `sources.py`, keep
   only AI-relevant ones, bucket them into 24h / 7d / 30d.
2. **Judge** — an LLM ranks them and writes the top 5 per window (the month
   window becomes 5 synthesised themes), each decoded into plain English and
   tagged with concepts.

Output is written to `../public/martech-news.json`, which the page reads.

## The one key you need

The agent calls Anthropic. Set this before running — locally and as a repo secret:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

That's the only credential required. (Optionally `DECODER_MODEL`, default
`claude-sonnet-4-6`.)

## Run it locally

```bash
cd agent
pip install -r requirements.txt
python agent.py          # writes ../public/martech-news.json
```

Then preview the page: `npm run dev` → `/projects/martech-ai-news`.

## Run it automatically (recommended)

`.github/workflows/refresh-news.yml` runs the agent every day at 06:00 UTC and
on demand (Actions tab → "Refresh MarTech AI news" → Run workflow), then commits
the updated JSON so the live site picks it up.

**Connect the key once:** repo → Settings → Secrets and variables → Actions →
New repository secret → `ANTHROPIC_API_KEY`.

## The Refresh button

By default the in-page Refresh button re-fetches the latest committed
`martech-news.json` (i.e. the most recent daily/manual run).

To make Refresh **run the agent live** instead, deploy `server.py` (e.g. to a
Hugging Face Space, like your other agents) and paste its URL into
`REFRESH_ENDPOINT` near the top of the `<script>` block in
`martech-ai-news.astro`:

```js
const REFRESH_ENDPOINT = 'https://<your-space>.hf.space/refresh';
```

Until then, leave it empty — everything still works.

## Editing sources / concepts

- `FEEDS` in `sources.py` — add/remove feeds (any RSS/Atom URL).
- `CONCEPTS` in `sources.py` — the fixed taxonomy the judge tags against. This
  same dict is copied into the JSON and read by the page, so the two never drift.
