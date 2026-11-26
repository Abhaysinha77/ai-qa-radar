# Making changes to AI + QA Radar

## The easiest way: ask Claude
Open Claude (Cowork), give it access to this folder, and describe the change in plain words
("make the cards lighter", "add the Selenium YouTube channel as a source"). Then publish (step 5).

## Doing it yourself

### 1. One-time setup (Terminal)
```bash
cd ~/Documents/ME/ai-qa-radar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```
Optional but recommended editor: **VS Code** (https://code.visualstudio.com) → File → Open Folder → `ai-qa-radar`.

### 2. Where things live
| I want to change… | Edit this file | What to look for |
|---|---|---|
| Colours, gradient, fonts, spacing | `web/app.css` | The variables at the top: `--accent`, `--accent2`, `--grad`, `--bg`, `--card` (light theme first, dark theme below it) |
| Text, layout, what each tab shows | `web/app.js` | Functions `renderHot` (Briefing), `renderToday` (Feed), `renderTrends`, `renderLearn`, `renderLibrary`, `readerHtml` (summary view), `card` |
| The page shell (menu, header) | `web/index.html` | |
| News sources (RSS/Atom feeds) | `digest/config.py` | `RELEASE_FEEDS`, `OFFICIAL_FEEDS`, `BLOG_FEEDS`, `RESEARCH_FEEDS` — add `("Name", "https://feed-url", None)` |
| Hacker News topics | `digest/config.py` | `TOPICS` — name, search words, minimum points, words to exclude |
| What counts as urgent / important | `digest/config.py` | `RANKING`, `TAGS` (then run `python -m tests.test_scoring_contract`) |
| Free courses | `digest/config.py` | `LEARNING` |
| Library resources | `digest/config.py` | `RESOURCES` |
| Glossary terms | `digest/config.py` | `GLOSSARY` |
| How often it refreshes | `.github/workflows/daily.yml` | the `cron:` line (UTC) |

### 3. See your change on your computer
```bash
source .venv/bin/activate
python -m server
```
Open http://localhost:8000. The first collection takes 1–2 minutes. After editing files in `web/`,
stop the server (Ctrl + C) and start it again, then reload the page.

### 4. Check nothing broke
```bash
pytest -q
node --test tests/js/*.test.mjs
```
(`node` comes from `brew install node` if you don't have it.) GitHub runs these too — a failing
test stops the deploy, so the live app never breaks.

### 5. Publish
```bash
./publish.sh --user Abhaysinha77
```
Live about 3 minutes later. Undo a bad change: `git checkout -- <file>` before publishing, or ask Claude.
