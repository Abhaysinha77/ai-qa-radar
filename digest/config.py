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
        {"pattern": r"\bpytest\b|\bplaywright\b|\bselenium\b|webdriver", "weight": 35},
        {"pattern": r"test automation|flaky|end-to-end|\be2e\b|\bqa\b|quality assurance|testing", "weight": 22},
        {"pattern": r"\bmcp\b|model context protocol", "weight": 25},
        {"pattern": r"coding agent|claude code|\bcodex\b|copilot|\bcursor\b", "weight": 20},
        {"pattern": r"\bevals?\b|benchmark|llm testing|red[- ]team", "weight": 20},
        {"pattern": r"\bagents?\b|agentic", "weight": 16},
        {"pattern": r"anthropic|\bclaude\b|openai|\bgpt", "weight": 16},
        {"pattern": r"\brag\b|retrieval|embedding|vector", "weight": 14},
        {"pattern": r"\bpython\b|\bpypi\b", "weight": 14},
        {"pattern": r"\bllms?\b|\bai\b|\bmodels?\b", "weight": 6},
    ],
    # how time-sensitive it is (urgency = highest matching category)
    "urgency": [
        {"label": "Security", "pattern": r"security|\bcve\b|vulnerab|exploit|breach|incident|compromis|malware", "weight": 70},
        {"label": "Breaking change", "pattern": r"breaking|removed|removal|deprecat|end[- ]of[- ]life|\beol\b|retir|sunset|shut ?down", "weight": 60},
        {"label": "Privacy", "pattern": r"silently|re-?enabl|data sharing|training on|telemetry", "weight": 50},
        {"label": "Outage", "pattern": r"outage|degraded|\bdown\b", "weight": 45},
    ],
    "release_urgency": 30,     # a new version of a tool you use
    "official_boost": 10,      # releases + official vendor posts
    "fresh_hours": 24,         # extra urgency for things from the last day
    "fresh_boost": 10,
    "act_urgency": 50,         # quadrant thresholds
    "act_importance": 45,
}
