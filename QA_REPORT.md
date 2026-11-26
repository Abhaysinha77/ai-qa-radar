# QA Report — Kairoq

**Date:** 2026-11-26 · **Build under test:** current `main` (collector + web app) · **Verdict:** ✅ Ready to deploy, with the residual risks listed at the end.

## 1. Scope and approach

Risk-based testing of the whole flow: **sources → collector (fetch, parse, merge, remember, rank, summarise) → data.json → phone app (render, live refresh, actions, storage) → hosting workflow.**

| Level | What | How |
|---|---|---|
| Static review | Every Python module, `app.js`, service worker, workflow | Line-by-line read; risks turned into tests |
| Unit | Parsers, de-duplication, state, ranking, summaries, notify, config | `pytest` (offline) |
| Negative | Malformed/HTML-instead-of-feed, empty pages, missing fields, timeouts, total outage, corrupted state, blocked storage, server 500, offline | `pytest` + `node:test` |
| Edge | Boundaries (score thresholds, 200-word cap), unicode/emoji/RTL, 300-char unbroken titles, 10⁹ points, future/invalid dates, duplicate hits, version-number titles | `pytest` + `node:test` + browser screenshots |
| Property / fuzz | 500 random titles/groups/points → scores always 0–100, valid quadrant | `pytest` |
| End-to-end (collector) | The **real** collector with all ~70 jobs and threads against a simulated internet: happy path, broken sources, rerun same day, next day, new version, archive expiry, total outage, volume | `tests/test_e2e_collector.py` |
| End-to-end (app) | The **real** `app.js` in a sandbox with fake DOM, storage and network | `tests/js/app.test.mjs` |
| Contract | Python and JavaScript must score and tag identically | `tests/fixtures/scoring_cases.json` read by both sides |
| Security | XSS in titles/summaries/sources/tags, `javascript:`/`data:` URLs, script in feed bodies, prompt-injection guard in summary prompt | unit + app tests + browser |
| Visual | Hostile data rendered in a real browser (XSS payloads, 300-char words, 5 failed sources, huge numbers, mixed scripts) | screenshots |
| Performance | 1,171 candidate stories in one run, then a rerun against the grown archive | timed E2E test |
| Config / CI | Workflow YAML parses, manifest JSON valid, source names unique, all URLs https | scripted checks |

## 2. Results

| Suite | Tests | Result |
|---|---|---|
| Python — original suite | 38 | ✅ pass |
| Python — QA unit / negative / edge / fuzz | 45 | ✅ pass |
| Python — end-to-end collector | 6 | ✅ pass |
| Python — scoring contract | 2 | ✅ pass |
| Python — backend server over real HTTP (routes, headers, path traversal, stale-while-revalidate, rate limit, 10 concurrent refreshes, failure, atomic reads, full stack with real collector) | 11 | ✅ pass (3 consecutive runs) |
| JavaScript — app behaviour | 16 | ✅ pass |
| JavaScript — scoring contract | 10 | ✅ pass |
| **Total** | **128** | **✅ 128 / 128** |

Also smoke-tested `python -m server` as a real process: `/` 200, `/api/health` 200,
`/data.json` 503 while the first collection runs, `/api/status` reports progress.
`publish.sh` tested for syntax, the "no git identity" path and the "no GitHub CLI" path;
it commits 42 files and never commits `site/` or `state/`.

**Performance:** 1,171 candidates → 110 shown in ~6 s; rerun with archive ~9 s (sandbox CPU). Well under the 30-minute schedule.

## 3. Defects found and fixed

| ID | Severity | Area | Defect | Fix | Covered by |
|---|---|---|---|---|---|
| D1 | **High** | Collector | The "5 per section" cap also applied to Releases and blogs, so some new releases and the last blog feeds in the list (Python Insider, Real Python…) were **never shown** — same order every run, starved forever. | Cap only Hacker News sections; feeds are already limited per source. | `test_e2e_happy_path_and_broken_sources` |
| D2 | **High** | Collector | Cap "leak": the collector runs every 30 min and each run topped HN sections up by another 5, so noise grew all day. | Cap is now **per day**, counting what was already shown today. | `test_e2e_rerun_same_day_and_next_day_never_repeats` |
| D3 | **High** | De-duplication | Fuzzy title matching treated *"OpenAI SDK v3.59.0"* and *"v3.58.0"* (or *Claude 5.2* vs *5.1*) as the same story → **new versions were hidden** as "already seen". | Titles with different numbers are never merged; cheap length pre-check added (also faster). | `test_same_story_never_merges_different_versions`, `test_e2e_new_version_next_day_is_shown` |
| D4 | Medium | State | A damaged `seen.json` crashed the whole build → site stops updating. | Recover automatically, keep a `.corrupt` copy, start fresh. | `test_corrupted_state_file_is_recovered_not_fatal` |
| D5 | Medium | Summaries | An empty AI answer was saved as a blank "summary". | Falls back to an excerpt. | `test_empty_ai_answer_falls_back_to_excerpt` |
| D6 | Low | Summaries | "Skip X/Twitter" rule matched any URL containing `x.com/` (e.g. `dropbox.com/`), so those articles were never summarised. | Host-based check. | `test_skip_fetch_only_matches_real_hosts` |
| D7 | Low | App UX | A muted topic still appeared in Hot/Today if that card had been saved. | Muted topics leave every feed; Saved keeps them. | `save, read and mute work and persist` |
| D8 | Low | App UI | Very long unbroken words overflowed cards on phones (horizontal scroll). | `overflow-wrap:anywhere` on cards and tables. | Browser screenshot (before/after) |
| D9 | Low | App | "New since last visit" relied on `pagehide`, which iOS home-screen apps often skip → stale NEW badges. | Also saved when the app is hidden. | Code review (needs a real iPhone to confirm) |
| D10 | Medium | Backend | Race: opening the app while a refresh was writing `data.json` could return a half-written (invalid) file. Found by the server tests. | Atomic writes (temp file + swap) for `data.json` and the memory file. | `test_reader_never_sees_a_half_written_file` |

No open defects.

## 4. Key scenarios verified

**Positive:** releases, vendor posts, blogs, research, HN topics and sections collected; one story found in 3 places is **one card** in its most specific section with "also in"; breaking-change release and MCP security incident land in **Act now**; Hot shows the top 10, "Show all" shows the rest; search, save, read, mute, course progress; live HN adds relevant new stories on open.

**Negative:** malformed feed, HTML instead of RSS, timeout, 404, HN page layout change (0 rows), total outage → page still builds and every failure is named with a reason; offline with/without cache; data.json HTTP 500; storage blocked/corrupted; live HN down.

**Edge:** Nightly/rc builds, theatre "playwright", off-topic and duplicate live hits filtered; boundaries at exactly urgency 50 / importance 45; 200 vs 201 words; empty titles; unicode/emoji/Arabic/Japanese; 999,999 points; dates in the future or unparseable; items expire from the page after 7 days but are still remembered (never re-shown).

**Security:** all user-visible text is escaped (`<script>`, `<img onerror>`, `<svg onload>` rendered as text in a real browser); `javascript:`, `data:` and protocol-relative links become `#`; feed HTML stripped to text; summary prompt tells the model to treat article text as untrusted.

## 5. Not covered / residual risks

| Risk | Why not covered here | How to close it |
|---|---|---|
| Real websites (feeds, HN markup, Algolia, HF API) | Test environment has no internet | First GitHub run → check **Saved+ → Sources**; any ✗ shows the reason |
| Real phones (iOS Safari home-screen app, Android Chrome), service-worker updates | No real browser engine for interaction tests here | 10-minute manual check after deploy (checklist below) |
| GitHub Actions execution (permissions, Pages, `data` branch push) | YAML validated, but not executed | First manual "Run workflow" |
| Live HN from the browser (CORS) | Assumed from public API behaviour | Header shows "● Live" or "live HN unavailable" |
| Accessibility audit with a screen reader | Not run | Labels and live regions are present; run VoiceOver/TalkBack once |

**Manual checklist after deploy (≈10 min):**
1. Open the URL on your phone → header shows "Updated … · ● Live".
2. Saved+ → Sources: all ✓ (note any ✗).
3. Tap a card title → opens the article; card dims as read.
4. Save one card, mute one topic, mark one course "Doing" → close and reopen → still there.
5. Add to Home Screen → open from the icon → works; turn on airplane mode → last data still shows.
6. Come back after 30+ minutes → header time updates by itself.

## 6. How to run the tests

```bash
pip install -r requirements-dev.txt
pytest -q                          # 102 Python tests (unit, edge, E2E, contract, server)
node --test tests/js/*.test.mjs    # 26 app tests (no npm install needed)
```
Both run automatically in GitHub Actions before every build; a failing test stops the deploy.
