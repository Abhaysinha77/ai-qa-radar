"""All sources and topics live here. Edit this file to add/remove things."""

# Time zone used for "today" and dates on the page (IANA name, e.g. "Asia/Kolkata").
TIMEZONE = "UTC"

# How many items to show per group, and how long things stay on the page.
MAX_PER_GROUP = 5
ARCHIVE_DAYS = 7          # items stay visible under "Last 7 days"
SEEN_RETENTION_DAYS = 120  # how long we remember an item so it never repeats
HN_TOPIC_WINDOW_HOURS = 48

USER_AGENT = "ai-qa-digest/1.0 (personal reader)"

# Summaries: every new item gets a plain-English summary (max 200 words).
# Set ANTHROPIC_API_KEY (or OPENAI_API_KEY + OPENAI_MODEL) as a GitHub secret to get AI
# summaries; without a key you get a short excerpt of the article instead.
ANTHROPIC_MODEL = "claude-haiku-5-5"   # override with the ANTHROPIC_MODEL env var
MAX_SUMMARIES_PER_RUN = 80             # cost guard
BACKFILL_PER_RUN = 25                  # re-read older stories that predate the full reader
READER_VERSION = 3                     # bump when the reader improves: older summaries are redone (a few per run)
STORY_MAX_WORDS = 600                  # "The full story": quoted, section by section, covers every paragraph
# Free AI summaries inside GitHub Actions (GitHub Models, uses the workflow's own GITHUB_TOKEN, no key to buy).
# The free tier is rate-limited, so we spend it carefully and fall back to quoted summaries when it runs out.
GITHUB_MODELS_MODEL = "openai/gpt-4.1-mini"   # override with the GITHUB_MODELS_MODEL variable
AI_PER_RUN = 12                        # at most this many AI summaries per 30-minute run
AI_PER_DAY = 120                       # ...and per day (stored in state, resets at midnight)

# ---------------------------------------------------------------- releases
# (display name, feed url, regex of titles to skip)
RELEASE_FEEDS = [
    ("Playwright (Python)", "https://github.com/microsoft/playwright-python/releases.atom", None),
    ("Playwright MCP", "https://github.com/microsoft/playwright-mcp/releases.atom", None),
    ("Selenium", "https://github.com/SeleniumHQ/selenium/releases.atom", r"(?i)nightly"),
    ("pytest", "https://pypi.org/rss/project/pytest/releases.xml", r"(?i)(dev|rc\d*|a\d+|b\d+)$"),
    ("MCP spec", "https://github.com/modelcontextprotocol/modelcontextprotocol/releases.atom", None),
    ("MCP Python SDK", "https://github.com/modelcontextprotocol/python-sdk/releases.atom", None),
    ("Anthropic Python SDK", "https://github.com/anthropics/anthropic-sdk-python/releases.atom", None),
    ("OpenAI Python SDK", "https://github.com/openai/openai-python/releases.atom", None),
]
RELEASE_MAX_AGE_DAYS = 45
RELEASES_PER_FEED = 2

# ---------------------------------------------------------- official feeds
# (display name, feed url, regex a title must match or None for all)
OFFICIAL_FEEDS = [
    ("OpenAI News", "https://openai.com/news/rss.xml", None),
    ("MCP Blog", "https://blog.modelcontextprotocol.io/index.xml", None),
    ("GitHub Changelog", "https://github.blog/changelog/feed/",
     r"(?i)actions|copilot|coverage|security|agent|codeql|dependabot|mcp"),
    ("PyPI Blog", "https://blog.pypi.org/feed_rss_created.xml", None),
    ("Microsoft Agent Framework", "https://devblogs.microsoft.com/agent-framework/feed/", None),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", r"(?i)agent|eval|rag|mcp|test|benchmark"),
]

# Pages that have no feed: shown as quick links at the bottom of the page.
CHECK_PAGES = [
    ("Claude API release notes", "https://platform.claude.com/docs/en/release-notes/overview"),
    ("Claude app release notes", "https://support.claude.com/en/articles/12138966-release-notes"),
    ("OpenAI API changelog", "https://developers.openai.com/changelog/"),
    ("OpenAI deprecations", "https://developers.openai.com/api/docs/deprecations"),
    ("Playwright Python release notes", "https://playwright.dev/python/docs/release-notes"),
    ("Selenium blog", "https://www.selenium.dev/blog/"),
    ("pytest changelog", "https://docs.pytest.org/en/stable/changelog.html"),
    ("Python What's New", "https://docs.python.org/3/whatsnew/"),
    ("Software Testing Weekly", "https://softwaretestingweekly.com/"),
    ("Gemini API changelog", "https://ai.google.dev/gemini-api/docs/changelog"),
]

# ------------------------------------------------------- practitioner blogs
BLOG_FEEDS = [
    ("Simon Willison", "https://simonwillison.net/atom/everything/", None),
    ("Hamel Husain", "https://hamel.dev/index.xml", None),
    ("Eugene Yan", "https://eugeneyan.com/rss/", None),
    ("Martin Fowler", "https://martinfowler.com/feed.atom", None),
    ("Google Testing Blog", "https://testing.googleblog.com/feeds/posts/default", None),
    ("Interconnects", "https://www.interconnects.ai/feed", None),
    ("Ahead of AI", "https://magazine.sebastianraschka.com/feed", None),
    ("Python Insider", "https://pythoninsider.blogspot.com/feeds/posts/default", None),
    ("Real Python", "https://realpython.com/atom.xml", r"(?i)test|pytest|ai|llm|agent|async|typing|3\.1\d"),
    ("Latent Space", "https://www.latent.space/feed", None),
    ("Import AI", "https://importai.substack.com/feed", None),
    ("Python Bytes", "https://pythonbytes.fm/episodes/rss", None),
    ("Playwright (dev.to)", "https://dev.to/feed/playwright", None),
    ("GitHub Blog · AI & ML", "https://github.blog/ai-and-ml/feed/", None),
]

# Research: only papers that look relevant to testing / agents / evals / code.
RESEARCH_FEEDS = [
    ("arXiv cs.SE", "https://rss.arxiv.org/rss/cs.SE",
     r"(?i)\btest|llm|agent|benchmark|eval|code generation|bug|fuzz"),
]
HF_DAILY_PAPERS = "https://huggingface.co/api/daily_papers"
HF_FILTER = r"(?i)agent|eval|benchmark|test|code|rag|retriev|tool"
RESEARCH_PER_FEED = 4
FEED_MAX_AGE_DAYS = 10
POSTS_PER_FEED = 3

# ------------------------------------------------------------ Hacker News
HN_SECTIONS = [
    ("Best (24h)", "https://news.ycombinator.com/best?h=24"),
    ("Front page", "https://news.ycombinator.com/news"),
    ("Active", "https://news.ycombinator.com/active"),
    ("Show HN", "https://news.ycombinator.com/show"),
    ("Ask HN", "https://news.ycombinator.com/ask"),
    ("Launches", "https://news.ycombinator.com/launches"),
    ("Pool", "https://news.ycombinator.com/pool"),
]
HN_BEST_COMMENTS = "https://news.ycombinator.com/bestcomments?h=24"

# A Hacker News section item is shown only if its title matches this.
RELEVANT = (
    r"(?i)\b(ai|llms?|gpt\w*|openai|anthropic|claude|gemini|models?|agents?|agentic|mcp|rag|"
    r"evals?|python|pytest|selenium|playwright|tests?|testing|qa|bugs?|ci|github|security|"
    r"vulnerab\w*|cve\w*|breach\w*|incident|outage|coding|copilot|codex|cursor|browser|"
    r"automation|api|benchmark\w*|inference|prompt\w*)\b"
)

# Topic searches (HN Algolia). name, queries, min points, regex to exclude.
TOPICS = [
    ("Python", ["python"], 30, r"(?i)monty python|snake"),
    ("pytest", ["pytest"], 1, None),
    ("Selenium", ["selenium"], 1, r"(?i)supplement|diet|mineral|soil"),
    ("Playwright", ["playwright"], 1, r"(?i)theat|broadway|stage|drama|dies|died|novel|pulitzer|stoppard"),
    ("Testing & QA", ["test automation", "software testing", "flaky tests", "end-to-end testing",
                      "fuzzing", "QA"], 15, None),
    ("MCP", ["MCP", "Model Context Protocol"], 10, r"(?i)minecraft"),
    ("RAG", ["RAG", "retrieval augmented", "vector search", "embeddings"], 10, r"(?i)rag ?doll|ragtime"),
    ("Evals & LLM testing", ["evals", "LLM eval", "LLM testing", "red teaming", "LLM benchmark"], 10, None),
    ("AI agents", ["AI agents", "agentic", "agent framework"], 40,
     r"(?i)\b(ice|fbi|cia|federal|secret|real estate|travel|border|undercover) agents?\b"),
    ("Coding agents", ["coding agent", "Claude Code", "Codex", "Copilot", "Cursor"], 40, None),
    ("OpenAI", ["OpenAI", "GPT"], 80, None),
    ("Anthropic / Claude", ["Anthropic", "Claude"], 80, None),
    ("Future of AI", ["AGI", "AI safety", "superintelligence", "future of AI"], 60, None),
    ("Free courses & offers", ["free course", "free certification", "free certificate",
                               "free tier", "free credits", "free for open source"], 10, None),
    # topics added because they sit exactly where AI meets QA
    ("AI security", ["prompt injection", "jailbreak", "LLM security", "AI red teaming"], 10, None),
    ("Browser & computer-use agents", ["computer use", "browser agent", "browser automation"], 10, None),
    ("LLM observability", ["LLM observability", "OpenTelemetry", "LLM tracing"], 10, None),
    ("Context engineering", ["context engineering", "agent skills", "AGENTS.md"], 10, None),
    ("Multi-agent & A2A", ["A2A protocol", "multi-agent", "agent to agent"], 10, None),
    ("API & contract testing", ["API testing", "contract testing", "OpenAPI"], 10, None),
    ("Performance testing", ["load testing", "performance testing", "k6"], 10, None),
    ("Accessibility testing", ["accessibility testing", "WCAG", "a11y"], 5, None),
    ("Mobile testing", ["Appium", "mobile testing", "Maestro mobile"], 3, None),
]

# ------------------------------------------------------- learn & free stuff
# Hand-picked FREE courses and certificates (cert = what you get for free).
# The app tracks your progress on each one. New free courses/tools/offers found by the
# collector (tag "Free & learning") appear under them automatically.
LEARNING = [
    {"title": "Anthropic Academy: MCP, Claude Code, API courses", "provider": "Anthropic",
     "url": "https://anthropic.skilljar.com/", "topics": ["MCP", "AI agents", "Coding agents"],
     "cert": "Certificate", "hours": "1–4 h each", "why": "MCP and Claude Code straight from the source."},
    {"title": "Hugging Face MCP Course", "provider": "Hugging Face",
     "url": "https://huggingface.co/learn/mcp-course/unit0/introduction", "topics": ["MCP"],
     "cert": "Certificate", "hours": "self-paced", "why": "Build and test MCP servers; pairs with Playwright MCP."},
    {"title": "Hugging Face AI Agents Course", "provider": "Hugging Face",
     "url": "https://huggingface.co/learn/agents-course/unit0/introduction", "topics": ["AI agents"],
     "cert": "Certificate", "hours": "self-paced", "why": "Agent fundamentals, frameworks and a final challenge."},
    {"title": "OpenAI Academy (AI fundamentals, agents, workflows)", "provider": "OpenAI",
     "url": "https://academy.openai.com/", "topics": ["AI agents", "OpenAI"],
     "cert": "Badge (80%+ on assessment)", "hours": "short courses", "why": "Free with a ChatGPT account."},
    {"title": "DeepLearning.AI: Evaluating AI Agents", "provider": "DeepLearning.AI",
     "url": "https://www.deeplearning.ai/courses/", "topics": ["Evals", "AI agents"],
     "cert": "Varies by course", "hours": "1–2 h", "why": "Structured evals for agents — core QA skill for AI."},
    {"title": "DeepLearning.AI: Building and Evaluating Advanced RAG", "provider": "DeepLearning.AI",
     "url": "https://www.deeplearning.ai/courses/", "topics": ["RAG", "Evals"],
     "cert": "Varies by course", "hours": "1–2 h", "why": "How to measure retrieval and answer quality."},
    {"title": "DeepLearning.AI: Agentic AI (Andrew Ng)", "provider": "DeepLearning.AI",
     "url": "https://www.deeplearning.ai/courses/", "topics": ["AI agents"],
     "cert": "Varies by course", "hours": "self-paced", "why": "Multi-step agent workflows explained clearly."},
    {"title": "Test Automation University (Selenium Python, pytest, Playwright)", "provider": "Applitools",
     "url": "https://testautomationu.applitools.com/", "topics": ["Testing & QA", "Selenium", "Playwright", "pytest"],
     "cert": "Certificate", "hours": "1–4 h each", "why": "Classic free test-automation courses with certificates."},
    {"title": "TestGuild Academy free courses", "provider": "TestGuild",
     "url": "https://testguild.com/training-courses/", "topics": ["Testing & QA", "Playwright", "Selenium"],
     "cert": "Certificate", "hours": "varies", "why": "Current Playwright and Selenium practice."},
    {"title": "Free Playwright course", "provider": "Great Learning",
     "url": "https://www.mygreatlearning.com/academy/learn-for-free/courses/playwright-test-automation",
     "topics": ["Playwright"], "cert": "Certificate", "hours": "~4 h", "why": "Quick beginner refresher."},
    {"title": "Playwright for Python — official tutorial", "provider": "Microsoft",
     "url": "https://playwright.dev/python/docs/intro", "topics": ["Playwright", "pytest"],
     "cert": "None", "hours": "self-paced", "why": "Always up to date with the latest release."},
    {"title": "Kaggle Learn: Python, ML and AI micro-courses", "provider": "Kaggle",
     "url": "https://www.kaggle.com/learn", "topics": ["Python", "AI agents"],
     "cert": "Certificate", "hours": "3–5 h each", "why": "Short, hands-on, free certificates."},
    {"title": "freeCodeCamp Python certification", "provider": "freeCodeCamp",
     "url": "https://www.freecodecamp.org/learn/", "topics": ["Python"],
     "cert": "Certification", "hours": "long", "why": "Free project-based Python certification."},
    {"title": "Microsoft Learn: Develop AI agents / AI agent fundamentals", "provider": "Microsoft",
     "url": "https://learn.microsoft.com/training/", "topics": ["AI agents"],
     "cert": "Free badge (exam is paid)", "hours": "3–7 h", "why": "Free training path and practice tests."},
    {"title": "GitHub Skills: Actions, Copilot and more", "provider": "GitHub",
     "url": "https://skills.github.com/", "topics": ["Coding agents", "Testing & QA"],
     "cert": "None", "hours": "under 1 h each", "why": "Hands-on labs for CI and Copilot inside GitHub."},
]
LEARNING_CHECKED = "2026-11-26"   # when these links/terms were last checked

# --------------------------------------------------------------- ranking
# Shared by the Python collector AND the web app (exported in data.json), so live items
# fetched on your phone are scored with exactly the same rules. Patterns must work in both
# Python and JavaScript and are matched case-insensitively against title + summary.
TAGS = {
    "pytest": r"\bpytest\b",
    "Playwright": r"\bplaywright\b",
    "Selenium": r"\bselenium\b|webdriver",
    "Testing & QA": r"\btest(s|ing)?\b|\bqa\b|flaky|end-to-end|\be2e\b|fuzz",
    "Python": r"\bpython\b|\bpypi\b|\bcpython\b",
    "MCP": r"\bmcp\b|model context protocol",
    "RAG": r"\brag\b|retrieval|embedding|vector (db|search|store)",
    "Evals": r"\bevals?\b|benchmark|red[- ]team",
    "AI agents": r"\bagents?\b|agentic",
    "Coding agents": r"coding agent|claude code|\bcodex\b|copilot|\bcursor\b|devin",
    "OpenAI": r"openai|\bgpt",
    "Anthropic": r"anthropic|\bclaude\b",
    "Security": r"security|\bcve\b|vulnerab|exploit|breach|malware|compromis",
    "AI security": r"prompt injection|jailbreak|guardrail|\bllm security|red[- ]team",
    "Browser agents": r"computer[- ]use|browser (agent|automation)|playwright mcp|\boperator agent",
    "Observability": r"observability|opentelemetry|\btracing\b|\btraces\b",
    "Context engineering": r"context engineering|context window|agent skills?|agents\.md|prompt engineering",
    "Multi-agent": r"multi[- ]agent|\ba2a\b|agent2agent|agent[- ]to[- ]agent",
    "API testing": r"api test|contract test|openapi|\bpact\b|postman",
    "Performance": r"load test|performance test|\bk6\b|locust|jmeter|latency",
    "Accessibility": r"accessibility|\ba11y\b|wcag|screen reader",
    "Mobile testing": r"appium|mobile test|xcuitest|espresso|maestro",
    "Free & learning": (
        r"free (course|class|certificat|training|tier|credits?|plan|access|usage|tool|api|ebook|book|workshop)|"
        r"\b(offers?|now|is|are|for|goes|went) free\b|"
        r"\bcourses?\b.{0,40}\bfree\b|\bfree\b.{0,40}\bcourses?\b|"
        r"open[- ]sourced\b|open[- ]sourcing|open[- ]weights?\b|\bacademy\b|no cost|\bfree credits\b"
    ),
}
# A tag is NOT applied when its exclude pattern matches (keeps "lock-free" etc. out of Learn).
TAG_EXCLUDE = {
    "Free & learning": r"lock[- ]free|wait[- ]free|free[- ]threading|free[- ]threaded|gil[- ]free|"
                       r"freedom|free speech|free will|hands[- ]free|duty[- ]free|cruelty[- ]free|"
                       r"sugar[- ]free|free fall|freelanc",
}
RANKING = {
    # how much each topic matters to YOUR work (importance points, capped at 60)
    "stack": [
        {"label": "Your test tools (pytest / Playwright / Selenium)", "pattern": r"\bpytest\b|\bplaywright\b|\bselenium\b|webdriver", "weight": 35},
        {"label": "Testing & QA", "pattern": r"test automation|flaky|end-to-end|\be2e\b|\bqa\b|quality assurance|testing", "weight": 22},
        {"label": "MCP", "pattern": r"\bmcp\b|model context protocol", "weight": 25},
        {"label": "Coding agents", "pattern": r"coding agent|claude code|\bcodex\b|copilot|\bcursor\b", "weight": 20},
        {"label": "Evals & LLM testing", "pattern": r"\bevals?\b|benchmark|llm testing|red[- ]team", "weight": 20},
        {"label": "AI agents", "pattern": r"\bagents?\b|agentic", "weight": 16},
        {"label": "OpenAI / Anthropic", "pattern": r"anthropic|\bclaude\b|openai|\bgpt", "weight": 16},
        {"label": "RAG", "pattern": r"\brag\b|retrieval|embedding|vector", "weight": 14},
        {"label": "Python", "pattern": r"\bpython\b|\bpypi\b", "weight": 14},
        {"label": "AI security & browser agents", "pattern": r"prompt injection|jailbreak|guardrail|computer[- ]use|browser (agent|automation)", "weight": 20},
        {"label": "API / performance / a11y / mobile testing", "pattern": r"api test|contract test|load test|performance test|accessibility|wcag|appium|mobile test", "weight": 18},
        {"label": "Observability, context & multi-agent", "pattern": r"observability|opentelemetry|context engineering|agent skills?|multi[- ]agent|\ba2a\b", "weight": 14},
        {"label": "General AI", "pattern": r"\bllms?\b|\bai\b|\bmodels?\b", "weight": 6},
    ],
    # how time-sensitive it is (urgency = highest matching category)
    "urgency": [
        {"label": "Security", "pattern": r"security|\bcve\b|vulnerab|exploit|breach|incident|compromis|malware", "weight": 70},
        {"label": "Breaking change", "pattern": r"breaking|removed|removal|deprecat|end[- ]of[- ]life|\beol\b|retir|sunset|shut ?down", "weight": 60},
        {"label": "Privacy", "pattern": r"silently|re-?enabl|data sharing|training on|telemetry", "weight": 50},
        {"label": "Outage", "pattern": r"outage|degraded|\bdown\b", "weight": 45},
    ],
    # For community/news items urgency words are only trusted in the TITLE (a long article that
    # merely mentions "removed" is not a breaking change). Releases/official posts use title+summary.
    "urgency_title_only_for_news": True,
    "release_urgency": 30,     # a new version of a tool you use
    "official_boost": 10,      # releases + official vendor posts
    "fresh_hours": 24,         # extra urgency for things from the last day
    "fresh_boost": 10,
    "act_urgency": 50,         # quadrant thresholds
    "act_importance": 45,
}

# ------------------------------------------------------------ resource library
# Hand-picked, all free to read/listen. Shown in the app's Library with what each is best for.
RESOURCES = [
    # official release notes & docs
    {"name": "Playwright for Python — release notes", "url": "https://playwright.dev/python/docs/release-notes", "kind": "Official", "topics": ["Playwright"], "about": "Every Playwright release with what changed for Python."},
    {"name": "Selenium blog", "url": "https://www.selenium.dev/blog/", "kind": "Official", "topics": ["Selenium"], "about": "Release posts, deprecations and Selenium 5 plans."},
    {"name": "pytest changelog", "url": "https://docs.pytest.org/en/stable/changelog.html", "kind": "Official", "topics": ["pytest"], "about": "Every pytest version, fixes and deprecations."},
    {"name": "Python — What's New", "url": "https://docs.python.org/3/whatsnew/", "kind": "Official", "topics": ["Python"], "about": "New language features per Python version."},
    {"name": "Model Context Protocol — spec & blog", "url": "https://modelcontextprotocol.io/", "kind": "Official", "topics": ["MCP"], "about": "The MCP specification, SDKs and security best practices."},
    {"name": "Claude API release notes", "url": "https://platform.claude.com/docs/en/release-notes/overview", "kind": "Official", "topics": ["Anthropic"], "about": "New models, API features and deprecations."},
    {"name": "OpenAI API changelog", "url": "https://developers.openai.com/changelog/", "kind": "Official", "topics": ["OpenAI"], "about": "API changes, new models and deprecations."},
    {"name": "GitHub Changelog", "url": "https://github.blog/changelog/", "kind": "Official", "topics": ["Coding agents", "Testing & QA"], "about": "Actions, Copilot and security changes that affect CI."},
    # practitioners
    {"name": "Simon Willison's blog", "url": "https://simonwillison.net/", "kind": "Blog", "topics": ["AI agents", "Coding agents"], "about": "Hands-on, honest notes on LLM tools as they ship."},
    {"name": "Hamel Husain — evals", "url": "https://hamel.dev/", "kind": "Blog", "topics": ["Evals"], "about": "The most practical writing on evaluating LLM apps."},
    {"name": "Eugene Yan", "url": "https://eugeneyan.com/writing/", "kind": "Blog", "topics": ["Evals", "RAG"], "about": "Deep posts on LLM systems, evals and retrieval."},
    {"name": "Martin Fowler — testing", "url": "https://martinfowler.com/tags/testing.html", "kind": "Blog", "topics": ["Testing & QA"], "about": "Timeless test-design thinking, now including AI agents."},
    {"name": "Google Testing Blog", "url": "https://testing.googleblog.com/", "kind": "Blog", "topics": ["Testing & QA"], "about": "Short, practical testing tips from Google engineers."},
    {"name": "Brian Okken — PythonTest", "url": "https://pythontest.com/", "kind": "Blog", "topics": ["pytest"], "about": "pytest and TDD from the author of the pytest book."},
    # newsletters & podcasts
    {"name": "Software Testing Weekly", "url": "https://softwaretestingweekly.com/", "kind": "Newsletter", "topics": ["Testing & QA"], "about": "The best weekly roundup of testing news."},
    {"name": "Latent Space", "url": "https://www.latent.space/", "kind": "Newsletter", "topics": ["AI agents"], "about": "AI engineering news and long interviews."},
    {"name": "Interconnects", "url": "https://www.interconnects.ai/", "kind": "Newsletter", "topics": ["AI agents"], "about": "How new models are trained and evaluated."},
    {"name": "Ahead of AI", "url": "https://magazine.sebastianraschka.com/", "kind": "Newsletter", "topics": ["AI agents"], "about": "Clear technical explainers on LLM internals."},
    {"name": "Import AI", "url": "https://importai.substack.com/", "kind": "Newsletter", "topics": ["AI agents"], "about": "Weekly research digest and future-of-AI analysis."},
    {"name": "Python Bytes (podcast)", "url": "https://pythonbytes.fm/", "kind": "Podcast", "topics": ["Python", "pytest"], "about": "Weekly Python tooling news in 30 minutes."},
    {"name": "Dwarkesh Podcast", "url": "https://www.dwarkesh.com/", "kind": "Podcast", "topics": ["AI agents"], "about": "Long-form interviews on where AI is heading."},
    # data & research
    {"name": "Artificial Analysis", "url": "https://artificialanalysis.ai/", "kind": "Data", "topics": ["Evals"], "about": "Compare models on quality, speed and price."},
    {"name": "Hugging Face Daily Papers", "url": "https://huggingface.co/papers", "kind": "Research", "topics": ["Evals", "AI agents"], "about": "The day's most discussed AI papers."},
    {"name": "arXiv cs.SE (software engineering)", "url": "https://arxiv.org/list/cs.SE/recent", "kind": "Research", "topics": ["Testing & QA"], "about": "New research on testing and AI for code."},
    # standards & security
    {"name": "OWASP GenAI Security Project", "url": "https://genai.owasp.org/", "kind": "Standard", "topics": ["AI security", "Security"], "about": "Top 10 risks for LLM apps and agents — use as a test checklist."},
    {"name": "MITRE ATLAS", "url": "https://atlas.mitre.org/", "kind": "Standard", "topics": ["AI security"], "about": "Catalogue of real attacks on AI systems."},
    # tools to test AI
    {"name": "DeepEval", "url": "https://github.com/confident-ai/deepeval", "kind": "Tool", "topics": ["Evals", "pytest"], "about": "LLM/RAG/agent metrics written as pytest tests."},
    {"name": "Ragas", "url": "https://github.com/explodinggradients/ragas", "kind": "Tool", "topics": ["RAG", "Evals"], "about": "Scores retrieval and answer quality for RAG."},
    {"name": "promptfoo", "url": "https://github.com/promptfoo/promptfoo", "kind": "Tool", "topics": ["AI security", "Evals"], "about": "Prompt regression tests and red-teaming in CI."},
    {"name": "Inspect (UK AISI)", "url": "https://github.com/UKGovernmentBEIS/inspect_ai", "kind": "Tool", "topics": ["Evals", "AI agents"], "about": "Python framework for repeatable agent evals."},
    {"name": "Playwright MCP", "url": "https://github.com/microsoft/playwright-mcp", "kind": "Tool", "topics": ["Playwright", "MCP", "Browser agents"], "about": "Lets AI agents drive a real browser."},
    # communities
    {"name": "Ministry of Testing", "url": "https://www.ministryoftesting.com/", "kind": "Community", "topics": ["Testing & QA"], "about": "The largest testing community: talks, articles, events."},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/", "kind": "Community", "topics": ["AI agents", "Testing & QA"], "about": "Where new tools and debates show up first."},
]

# ------------------------------------------------------------------ glossary
# New and important terms, in plain English. "match" finds the term in news; "tags" link it to
# topics. Definitions are hand-written and kept short; edit freely.
GLOSSARY = [
    {"term": "MCP (Model Context Protocol)", "match": r"\bmcp\b|model context protocol", "tags": ["MCP"], "def": "An open protocol that lets AI apps plug into tools and data through 'MCP servers' that expose tools, resources and prompts. The 2026-07-28 version made the protocol core stateless."},
    {"term": "MCP server", "match": r"mcp servers?", "tags": ["MCP"], "def": "A small service that offers tools (actions), resources (data) and prompts to any MCP-compatible AI app — e.g. Playwright MCP lets an agent control a browser."},
    {"term": "A2A (Agent2Agent)", "match": r"\ba2a\b|agent2agent", "tags": ["Multi-agent"], "def": "An open protocol for AI agents from different vendors to discover each other and hand tasks back and forth. MCP connects an agent to tools; A2A connects agents to agents."},
    {"term": "AI agent", "match": r"\bai agents?\b", "tags": ["AI agents"], "def": "A program where an LLM repeatedly plans, calls tools, looks at the results and decides the next step until a goal is done."},
    {"term": "Agentic workflow", "match": r"agentic", "tags": ["AI agents"], "def": "A process where the model decides the steps itself (loops, tool calls, retries) instead of following one fixed prompt."},
    {"term": "Agent harness", "match": r"\bharness\b", "tags": ["AI agents", "Coding agents"], "def": "The software around a model that runs its loop: tools, permissions, context and memory. The same model can perform very differently in different harnesses."},
    {"term": "Agent skills", "match": r"agent skills?|skill\.md", "tags": ["Context engineering"], "def": "Packaged folders of instructions and scripts (a SKILL.md file) that an agent loads only when a task needs them."},
    {"term": "AGENTS.md", "match": r"agents\.md", "tags": ["Context engineering", "Coding agents"], "def": "A markdown file in a repository that tells coding agents how to build, test and follow the project's conventions."},
    {"term": "Context engineering", "match": r"context engineering", "tags": ["Context engineering"], "def": "Deliberately choosing what goes into the model's context window — instructions, retrieved documents, tool results, memory — so it behaves reliably."},
    {"term": "Context window", "match": r"context window", "tags": ["Context engineering"], "def": "The maximum amount of text (in tokens) a model can consider at once, including your prompt and its answer."},
    {"term": "Tool calling", "match": r"tool call|function call", "tags": ["AI agents"], "def": "When a model returns a structured request to run a function (search, click, query a DB); your code runs it and sends back the result."},
    {"term": "Computer use / browser agent", "match": r"computer[- ]use|browser agents?", "tags": ["Browser agents"], "def": "An agent that operates a real screen or browser — reading the page and clicking/typing — instead of calling APIs."},
    {"term": "Coding agent", "match": r"coding agents?", "tags": ["Coding agents"], "def": "An agent that reads a codebase, edits files, runs tests and iterates — e.g. Claude Code, Codex, Copilot's agent mode."},
    {"term": "Vibe coding", "match": r"vibe[- ]cod", "tags": ["Coding agents"], "def": "Building software mainly by prompting an AI and accepting its code with little review (term coined by Andrej Karpathy in 2025). Raises the importance of testing."},
    {"term": "RAG (Retrieval-Augmented Generation)", "match": r"\brag\b|retrieval[- ]augmented", "tags": ["RAG"], "def": "Look up relevant documents first, then give them to the model so its answer is based on your data instead of memory."},
    {"term": "Embeddings", "match": r"embeddings?", "tags": ["RAG"], "def": "Lists of numbers that represent meaning, so similar texts end up close together — the basis of semantic search in RAG."},
    {"term": "Vector database", "match": r"vector (db|database|store|search)", "tags": ["RAG"], "def": "A database built to store embeddings and quickly find the most similar ones."},
    {"term": "Reranking / hybrid search", "match": r"rerank|hybrid search", "tags": ["RAG"], "def": "Combining keyword and semantic search, then re-ordering results with a second model to put the best passages first."},
    {"term": "Evals", "match": r"\bevals?\b", "tags": ["Evals"], "def": "Repeatable tests for AI behaviour: a set of inputs plus a way to score outputs, run on every change — the AI version of a regression suite."},
    {"term": "LLM-as-a-judge", "match": r"llm[- ]as[- ]a?[- ]?judge", "tags": ["Evals"], "def": "Using a model to grade another model's output against criteria. Useful at scale, but the judge itself must be checked against human labels."},
    {"term": "Golden dataset", "match": r"golden (data ?set|set)", "tags": ["Evals"], "def": "A curated set of inputs with known-good answers used as the baseline for evals."},
    {"term": "Benchmark contamination", "match": r"contaminat|benchmark(s)? leak", "tags": ["Evals"], "def": "When test questions leaked into a model's training data, so high scores don't reflect real ability."},
    {"term": "Hallucination", "match": r"hallucinat", "tags": ["Evals"], "def": "A confident answer that isn't supported by facts or the provided sources."},
    {"term": "Grounding / faithfulness", "match": r"grounded|faithfulness", "tags": ["RAG", "Evals"], "def": "Whether an answer sticks to the provided sources. A core metric for testing RAG."},
    {"term": "Prompt injection", "match": r"prompt injection", "tags": ["AI security"], "def": "Hidden instructions in text the model reads (a web page, email, file, tool output) that try to override its real instructions. The #1 risk for agents."},
    {"term": "Jailbreak", "match": r"jailbreak", "tags": ["AI security"], "def": "A prompt crafted to make a model ignore its safety rules."},
    {"term": "Guardrails", "match": r"guardrails?", "tags": ["AI security"], "def": "Checks around a model — input filters, output validation, permission limits — that block unsafe or off-policy behaviour."},
    {"term": "AI red teaming", "match": r"red[- ]team", "tags": ["AI security", "Evals"], "def": "Deliberately attacking an AI system (injection, jailbreaks, data leaks) to find weaknesses before users do."},
    {"term": "Distillation", "match": r"distill", "tags": ["AI agents"], "def": "Training a smaller model on the outputs of a larger one so it imitates it cheaply. Many providers' terms forbid doing this with their models."},
    {"term": "Open-weight model", "match": r"open[- ]weights?", "tags": ["AI agents"], "def": "A model whose trained weights you can download and run yourself (the training data and code may still be closed)."},
    {"term": "LLM observability", "match": r"observability|opentelemetry", "tags": ["Observability"], "def": "Tracing every prompt, tool call, latency and cost in production so you can debug and test AI behaviour after release."},
    {"term": "Self-healing tests", "match": r"self[- ]healing", "tags": ["Testing & QA"], "def": "UI tests that automatically repair broken locators or steps, often with AI, when the app changes."},
    {"term": "Flaky test", "match": r"flaky", "tags": ["Testing & QA"], "def": "A test that passes and fails on the same code — usually timing, shared state or environment problems."},
    {"term": "Mutation testing", "match": r"mutation testing", "tags": ["Testing & QA"], "def": "Making small deliberate bugs in code to check that your tests catch them — measures test quality, not just coverage."},
    {"term": "Property-based testing", "match": r"property[- ]based", "tags": ["Testing & QA", "Python"], "def": "Describing rules that must always hold and letting a tool (e.g. Hypothesis for Python) generate hundreds of inputs to try to break them."},
    {"term": "Deterministic simulation testing", "match": r"deterministic simulation", "tags": ["Testing & QA"], "def": "Running a whole system inside a controllable simulation (time, network, failures) so rare bugs can be found and replayed exactly."},
    {"term": "WebDriver BiDi", "match": r"bidi\b|webdriver bidi", "tags": ["Selenium", "Playwright"], "def": "The new W3C browser-automation protocol with two-way events (console, network) — the standard Selenium and browsers are moving to."},
    {"term": "Free-threading (no-GIL Python)", "match": r"free[- ]threading|no[- ]gil|\bgil\b", "tags": ["Python"], "def": "A CPython build without the Global Interpreter Lock, so threads can truly run in parallel (PEP 703)."},
    {"term": "Lazy imports", "match": r"lazy imports?", "tags": ["Python"], "def": "Python 3.15 feature (PEP 810): a 'lazy' import loads the module only when it's first used, making start-up faster."},
    {"term": "Synthetic test data", "match": r"synthetic (test )?data", "tags": ["Testing & QA"], "def": "Realistic but artificial data generated (often by AI) for testing, so you don't use real customer data."},
    {"term": "Shift-left testing", "match": r"shift[- ]left", "tags": ["Testing & QA"], "def": "Testing earlier in development — in design, code review and CI — instead of only at the end."},
]

TRENDS_WINDOW_DAYS = 7
TRENDS_HISTORY_DAYS = 60
# words that look like acronyms/products but are not interesting trends
TREND_STOPLIST = {
    "AI", "API", "HN", "US", "UK", "EU", "CEO", "CTO", "YC", "AND", "THE", "FOR", "NEW", "PDF", "HTML",
    "CSS", "JS", "URL", "HTTP", "HTTPS", "USA", "TV", "PC", "OK", "FAQ", "README", "GPU", "CPU", "SQL",
    "JSON", "LLM", "LLMS", "IT", "IS", "OF", "IN", "TO", "ON", "AT", "BY", "AN", "VS", "ID", "UI", "UX",
    "Ask", "Show", "Tell", "Launch", "GitHub", "Google", "Apple", "Microsoft", "Amazon", "Meta",
}
