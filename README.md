# Kairoq

*Kairoq* (KAI-rock) = **kairos**, Greek for "the right moment", + **Q** for quality. The AI & QA news that matters, at the moment it matters.

A free, full-stack web app for your phone: what's new in **Python, pytest, Selenium,
Playwright, AI agents, MCP, RAG, evals, OpenAI and Anthropic**, ranked by how **urgent** and
how **important** it is for a QA engineer, with plain-English summaries, free courses, and
no repeats.

## Publish it live — free, one command

```bash
cd ai-qa-radar
./publish.sh --user <your-personal-github-username>                 # public + GitHub Pages
./publish.sh --user <your-personal-github-username> --private       # private + Cloudflare Pages
# extras: --name my-repo   --setup-identity (personal git identity for all repos in the parent folder)
```

Before anything is pushed it **scans the project** for company names, internal links, work
emails and secrets (add your own words with `COMPANY_TERMS="word1|word2" ./publish.sh …`), and
after pushing it **verifies on GitHub** that every commit uses your private noreply email.
Private mode collects every 2 hours instead of every 30 minutes, to stay inside the 2,000 free
Actions minutes private repos get each month.

**Before publishing a side project made on a work laptop,** check your employer's
outside-work / side-project policy (or ask your manager). If in doubt, use `--private`.

It creates a **public** repo on your **personal** GitHub, pushes, turns on GitHub Pages and
starts the first build. About 3 minutes later the app is live at
`https://<your-username>.github.io/ai-qa-radar/`. On your phone: open it → Share →
**Add to Home Screen**. Run the same command again to publish later changes.

**Safe if your company account is logged in to the GitHub CLI:** the script adds your personal
account alongside it (first run only), switches to it for this push, and switches back at the
end. Commits use your personal GitHub *noreply* email set for this folder only (your global/work
git identity is untouched), company signing keys and keychain credentials are not used, and if
the wrong account signs in, it stops before pushing anything. Needs `git` and `gh`
(`brew install gh`; `brew upgrade gh` if it's old).

## What's inside (one project, frontend + backend)

```
ai-qa-radar/
├── web/            FRONTEND — installable app (HTML/CSS/JS, offline support, no framework)
├── digest/         BACKEND — collector: fetch → de-duplicate → rank → summarise → data.json
├── server/         BACKEND — API server: serves the app + data, refreshes in the background
├── tests/          102 Python tests (unit, edge, end-to-end, server over real HTTP)
├── tests/js/       26 app tests (Node's built-in runner, no npm)
├── .github/workflows/daily.yml   runs tests, collects every 30 min, deploys
├── render.yaml     optional: run the API server on Render's free plan
├── Dockerfile      optional: run it anywhere with Docker
├── publish.sh      one-command publish
└── QA_REPORT.md    test approach, results, defects found and fixed
```

## What's new in v2

- **Design:** dark/light (◐), a sticky top navigation bar on desktop and tablet, bottom tabs on
  phones, and a "Trending / Learn next" rail on wide screens.
- **Cards:** a short summary plus up to 3 key points, and a **Full briefing** button.
- **Full briefing:** *In short* (the gist), then **The full story** — the whole article, section by
  section, so you understand it without opening it — plus quoted Hacker News discussion, diagrams found in
  the article, terms explained, free courses, and *Why it's ranked here*.
- **Free AI summaries (GitHub Models):** the workflow asks GitHub Models (with its own token — nothing
  to buy) to write the full story in plain English, using only facts from the article. The free tier is
  rate-limited, so it does at most 12 per run / 120 per day (`AI_PER_RUN`, `AI_PER_DAY` in
  `digest/config.py`). Turn it off with the repository variable `GITHUB_MODELS = 0`.
- **Without AI it still works:** the full story is *quoted* — about one sentence in three from every
  paragraph, in order (short articles are kept whole) — so nothing is invented. Release notes become
  "Features / Bug fixes" bullets.
- **Trends & terms:** new and rising terms/tools/models this week (e.g. "A2A", "GPT-6.2") and a
  glossary of 40+ important concepts in plain English.
- **Library:** 30+ hand-picked free resources (official docs, blogs, newsletters, podcasts,
  tools, standards).
- **More topics:** AI security & prompt injection, browser/computer-use agents, LLM observability,
  context engineering, multi-agent/A2A, API/contract, performance, accessibility and mobile testing.
- **Smarter urgency:** for news items only the *title* can make something urgent, so a long article
  that merely mentions "removed" is no longer labelled "Breaking change".

## Tabs in the app

| Tab | What's in it |
|---|---|
| 🔥 **Hot** | Your top 10, in four boxes: **Act now** (urgent + important), **Watch**, **Plan**, **FYI**, with urgency/importance scores and the reason (Security, Breaking change, Privacy, Outage, New release). "Show all" for the rest. |
| 📰 **Today** | Everything new since your last visit, by source, or the last 7 days. |
| 🏷️ **Topics** | Filter or mute a topic. |
| 📦 **Releases** | New versions and official vendor posts, plus links to pages without feeds. |
| 🎓 **Learn** | Free courses and certificates with a progress tracker, plus "New free stuff spotted". |
| ⭐ **Saved+** | Saved cards, source health, settings, export/import. |

## Hosting options (all free)

| Option | How it refreshes | Sleeps? | Best for |
|---|---|---|---|
| **A. GitHub Pages + Actions** (default, `publish.sh`) | Backend collector runs on GitHub every 30 min; the app pulls live Hacker News every time you open it | **Never** — opens instantly | Daily use on your phone |
| **B. Render free web service** (`render.yaml`) | Real API server: refreshes every 30 min while awake, and whenever you open it with data older than 10 min | Yes — after 15 min idle; ~1 min to wake | A live API; also tap ↻ for a full refresh |
| **C. Your machine / Docker** | `python -m server` or `docker run` | No | Development, home server |

GitHub Actions is free and unlimited for public repos; Render's free plan gives 750 instance
hours a month and wipes its disk on restart (set `SEED_STATE_URL` to
`https://raw.githubusercontent.com/<you>/<repo>/data/seen.json` so it starts from GitHub's
memory and doesn't repeat stories).

**Option B steps:** render.com → New → **Blueprint** → pick your repo → Apply.

## Backend API (server mode)

| Method | Path | What it does |
|---|---|---|
| GET | `/` | The app |
| GET | `/data.json` | Latest data. If it's older than `STALE_MINUTES` (10), you get it instantly and a refresh starts in the background. `503` on the very first start while collecting. |
| POST | `/api/refresh` | Full refresh now. `202` started / already running, `429` + `Retry-After` if you refreshed less than 5 min ago. |
| GET | `/api/status` | Last refresh time, duration, counts, failed sources, last error |
| GET | `/api/health` | Liveness check |

Settings (environment variables): `PORT`, `REFRESH_MINUTES` (30), `STALE_MINUTES` (10),
`MIN_REFRESH_SECONDS` (300), `SEED_STATE_URL`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` +
`OPENAI_MODEL` (AI summaries).

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m server                        # http://localhost:8000
# tests
pytest -q && node --test tests/js/*.test.mjs
```

## Optional extras

- **AI summaries:** add secret `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` + variable
  `OPENAI_MODEL`) in GitHub → Settings → Secrets and variables → Actions. Without a key you
  get short excerpts.
- **Morning Telegram message:** secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`; variables
  `PAGE_URL`, `NOTIFY_HOUR_UTC` (default 2 = 07:30 IST).
- **Private instead of public:** Cloudflare Pages option — secrets `CLOUDFLARE_API_TOKEN`,
  `CLOUDFLARE_ACCOUNT_ID`, variable `DEPLOY_TARGET=cloudflare`. Private repos have a monthly
  Actions allowance, so change the cron to every 2 hours.

## Customise

Everything is in `digest/config.py`: feeds (`RELEASE_FEEDS`, `OFFICIAL_FEEDS`, `BLOG_FEEDS`,
`RESEARCH_FEEDS`), Hacker News `TOPICS`, ranking rules `RANKING` and `TAGS` (shared with the
app — after changing them run `python -m tests.test_scoring_contract`), and the free
`LEARNING` catalogue.

## Safety nets

- A failing source never breaks the app: the header says "N source(s) failed" and
  **Saved+ → Sources** shows which and why.
- Files are written atomically, so the app never reads a half-written update.
- A damaged memory file is set aside and rebuilt automatically.
- GitHub pauses schedules in quiet repos after 60 days; every run saves one fresh commit on
  the `data` branch to stay active (without growing history).
- All tests run before every deploy; a failing test stops the deploy.

MIT licensed.
