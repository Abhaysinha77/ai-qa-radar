// Tests for web/app.js with Node's built-in test runner (no npm packages):  node --test tests/js/
// The real app.js runs inside a sandbox with a tiny fake DOM, fake storage and fake network.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const SRC = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
const TODAY = new Date().toISOString().slice(0, 10);
const RANKING = {
  stack: [{ pattern: "\\bpytest\\b|\\bplaywright\\b|\\bselenium\\b", weight: 35 }, { pattern: "\\bmcp\\b", weight: 25 },
          { pattern: "\\bagents?\\b", weight: 16 }],
  urgency: [{ label: "Security", pattern: "security|breach|incident", weight: 70 },
            { label: "Breaking change", pattern: "breaking|deprecat|removed", weight: 60 }],
  release_urgency: 30, official_boost: 10, fresh_hours: 24, fresh_boost: 10, act_urgency: 50, act_importance: 45,
};

function makeItem(n, extra = {}) {
  return { key: `k${n}`, title: `pytest story ${n}`, url: `https://e/${n}`, source: "HN", group: "Topic · pytest",
    points: 10 + n, comments: n, discussion_url: `https://news.ycombinator.com/item?id=${n}`, also_in: [],
    first_seen: TODAY, found_at: new Date().toISOString(), summary: "", summary_kind: "", tags: ["pytest"],
    importance: 50, urgency: 20, quadrant: "Plan", hot: 40 + n, reasons: [], ...extra };
}

function makeData(items = [makeItem(1)], extra = {}) {
  return { generated: new Date().toISOString(), today: TODAY, summaries: "excerpt",
    groups: ["Releases", "Official updates", "Topic · pytest", "Topic · MCP"],
    tags: { pytest: "\\bpytest\\b", MCP: "\\bmcp\\b", "AI agents": "\\bagents?\\b", Security: "security|breach" },
    tag_exclude: {}, ranking: RANKING,
    live: { topics: [{ topic: "Playwright", exclude: "(?i)theat|dies" }], relevant: "\\b(mcp|pytest|playwright|agents?|ai)\\b" },
    check_pages: [{ name: "Docs", url: "https://docs" }], sources: [{ name: "A", group: "g", ok: true, count: 1 }],
    learning: { courses: [{ title: "Course", provider: "P", url: "https://c", topics: ["MCP"], cert: "Certificate", hours: "1 h", why: "w" }], checked: TODAY },
    items, ...extra };
}

class El {
  constructor(name) { this.name = name; this.innerHTML = ""; this.textContent = ""; this.handlers = {}; this.attrs = {};
    this.classes = new Set(); this.dataset = {}; this.value = "";
    this.classList = { toggle: (c, on) => (on === undefined ? (this.classes.has(c) ? this.classes.delete(c) : this.classes.add(c)) : on ? this.classes.add(c) : this.classes.delete(c)),
      contains: (c) => this.classes.has(c), add: (c) => this.classes.add(c), remove: (c) => this.classes.delete(c) }; }
  addEventListener(t, fn) { this.handlers[t] = fn; }
  setAttribute(k, v) { this.attrs[k] = v; }
  querySelector() { return new El("child"); }
  querySelectorAll() { return []; }
}

async function boot({ data = makeData(), fetchImpl, storage = {}, storageThrows = false, cache } = {}) {
  const els = { "#view": new El("view"), "#status": new El("status"), "#search": new El("search"), "#refresh": new El("refresh"), ".tabs": new El("tabs"), "#none": new El("none") };
  const store = { ...storage };
  if (cache) store["radar:cache"] = JSON.stringify(cache);
  const localStorage = {
    getItem: (k) => { if (storageThrows) throw new Error("SecurityError"); return k in store ? store[k] : null; },
    setItem: (k, v) => { if (storageThrows) throw new Error("QuotaExceeded"); store[k] = String(v); },
  };
  const calls = [];
  const defaultFetch = async (url) => {
    calls.push(url);
    if (url.startsWith("data.json")) return { ok: true, json: async () => data };
    return { ok: true, json: async () => ({ hits: [] }) };
  };
  const ctx = {
    console, Date, Math, JSON, Promise, Object, Array, Set, String, RegExp, Number, Error, encodeURIComponent,
    setTimeout: (fn) => 0, clearTimeout: () => {}, setInterval: () => 0,
    localStorage, location: { hash: "" }, history: { replaceState: () => {} }, navigator: {},
    confirm: () => true, alert: () => {}, Blob: class {}, URL: { createObjectURL: () => "" },
    fetch: async (u, o) => (fetchImpl ? (calls.push(u), fetchImpl(u, o)) : defaultFetch(u, o)),
    document: {
      querySelector: (s) => els[s] || new El(s), querySelectorAll: () => [], addEventListener: () => {},
      createElement: () => ({ click() {} }), visibilityState: "visible",
    },
    window: { addEventListener: () => {} },
  };
  ctx.window = { ...ctx.window, RADAR_DATA: undefined };
  ctx.globalThis = ctx;
  const exportLine = `\n;globalThis.__t={get data(){return data},get live(){return live},get liveState(){return liveState},
    render,loadData,loadLive,scoreItem,tagsFor,isNew,esc,safeUrl,prefs,card,
    setTab:(t)=>{tab=t},setQuery:(q)=>{query=q},setHotAll:(v)=>{hotAll=v}};`;
  vm.createContext(ctx);
  vm.runInContext(SRC + exportLine, ctx, { filename: "app.js" });
  await new Promise((r) => setImmediate(r)); await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  return { t: ctx.__t, els, store, calls };
}

const click = (els, target) => els["#view"].handlers.click({ target, preventDefault() {} });
const fakeTarget = (dataset, card) => ({ closest: (sel) => (sel === ".card" ? card : { dataset, closest: (s) => (s === ".card" ? card : null), textContent: "" }) });

// ------------------------------------------------------------------ safety
test("titles, summaries, sources and tags are HTML-escaped (XSS)", async () => {
  const evil = makeItem(1, { title: '<img src=x onerror="alert(1)">', summary: "<script>alert(2)</script>",
    source: "<b>x</b>", tags: ['"><svg onload=alert(3)>'], reasons: ["<i>r</i>"] });
  const { t } = await boot({ data: makeData([evil]) });
  const html = t.card(evil);
  assert.ok(!html.includes("<img src=x"), "raw img tag leaked");
  assert.ok(!html.includes("<script>"), "raw script leaked");
  assert.ok(!html.includes("<svg"), "raw svg leaked");
  assert.ok(html.includes("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"));
});

test("javascript:, data: and relative URLs are neutralised", async () => {
  const { t } = await boot();
  for (const bad of ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,x", "//evil.com", "", null, undefined])
    assert.equal(t.safeUrl(bad), "#", String(bad));
  assert.equal(t.safeUrl("https://ok.example/a?b=1"), "https://ok.example/a?b=1");
  const html = t.card(makeItem(2, { url: "javascript:alert(1)" }));
  assert.ok(!/href="javascript/i.test(html));
});

// ------------------------------------------------------------------ hot
test("Hot shows only the top 10 by score, then all on demand", async () => {
  const items = Array.from({ length: 25 }, (_, i) => makeItem(i, { hot: i, quadrant: ["Act now", "Plan", "Watch", "FYI"][i % 4] }));
  const { t, els } = await boot({ data: makeData(items) });
  t.setTab("hot"); t.render();
  const count = (els["#view"].innerHTML.match(/<article class="card/g) || []).length;
  assert.equal(count, 10);
  for (let i = 15; i < 25; i++) assert.ok(els["#view"].innerHTML.includes(`pytest story ${i}<`), `top item ${i} missing`);
  assert.ok(els["#view"].innerHTML.includes("Show all 25"));
  t.setHotAll(true); t.render();
  assert.equal((els["#view"].innerHTML.match(/<article class="card/g) || []).length, 25);
});

test("Hot with no data shows a friendly empty state", async () => {
  const { t, els } = await boot({ data: makeData([]) });
  t.setTab("hot"); t.render();
  assert.ok(els["#view"].innerHTML.includes("Nothing hot right now"));
});

// ------------------------------------------------------------------ NEW badge
test("NEW = found after last visit and not read", async () => {
  const lastVisit = new Date(Date.now() - 3600e3).toISOString();
  const { t } = await boot({ storage: { "radar:lastVisit": JSON.stringify(lastVisit), "radar:read": JSON.stringify(["k3"]) } });
  assert.equal(t.isNew(makeItem(1, { found_at: new Date().toISOString() })), true);
  assert.equal(t.isNew(makeItem(2, { found_at: new Date(Date.now() - 7200e3).toISOString() })), false);
  assert.equal(t.isNew(makeItem(3, { found_at: new Date().toISOString() })), false, "read items are never NEW");
});

// ------------------------------------------------------------------ live HN
test("live HN: adds relevant new stories, skips known, theatre and off-topic ones", async () => {
  const hits = [
    { objectID: "1", title: "pytest story 1", points: 50 },                         // already in data (same title)
    { objectID: "k-dup", title: "New MCP security incident hits agents", points: 300, url: "https://i" },
    { objectID: "k-dup", title: "New MCP security incident hits agents", points: 300, url: "https://i" }, // duplicate hit
    { objectID: "3", title: "Award-winning playwright dies at 88", points: 90 },
    { objectID: "4", title: "Best sourdough recipe", points: 900 },
    { objectID: "5", title: "", points: 10 },
  ];
  const { t } = await boot({ fetchImpl: async (u) => (u.startsWith("data.json")
    ? { ok: true, json: async () => makeData() } : { ok: true, json: async () => ({ hits }) }) });
  assert.equal(t.liveState, "ok");
  assert.equal(JSON.stringify(t.live.map((i) => i.title)), JSON.stringify(["New MCP security incident hits agents"]));
  const live = t.live[0];
  assert.equal(live.quadrant, "Act now");
  assert.ok(live.tags.includes("MCP") && live.url === "https://i");
});

test("live HN down: app still shows collected data and says so", async () => {
  const { t, els } = await boot({ fetchImpl: async (u) => {
    if (u.startsWith("data.json")) return { ok: true, json: async () => makeData() };
    throw new TypeError("Failed to fetch");
  } });
  assert.equal(t.liveState, "error");
  assert.ok(els["#status"].innerHTML.includes("live HN unavailable"));
  t.setTab("hot"); t.render();
  assert.ok(els["#view"].innerHTML.includes("pytest story 1"));
});

test("offline with no cache: clear error, no crash", async () => {
  const { els } = await boot({ fetchImpl: async () => { throw new TypeError("offline"); } });
  assert.ok(els["#view"].innerHTML.includes("Could not load data"));
});

test("offline with cache: last data is shown", async () => {
  const cached = makeData([makeItem(7, { title: "cached pytest story" })]);
  const { t, els } = await boot({ cache: cached, fetchImpl: async () => { throw new TypeError("offline"); } });
  t.setTab("hot"); t.render();
  assert.ok(els["#view"].innerHTML.includes("cached pytest story"));
});

test("server returns 500 for data.json: falls back to cache", async () => {
  const cached = makeData([makeItem(8, { title: "from cache" })]);
  const { t, els } = await boot({ cache: cached, fetchImpl: async (u) => ({ ok: !u.startsWith("data.json"), status: 500, json: async () => ({ hits: [] }) }) });
  t.setTab("hot"); t.render();
  assert.ok(els["#view"].innerHTML.includes("from cache"));
});

test("storage blocked (private mode): app still works", async () => {
  const { t, els } = await boot({ storageThrows: true });
  t.setTab("hot"); t.render();
  assert.ok(els["#view"].innerHTML.includes("pytest story 1"));
});

test("corrupted storage values do not break start-up", async () => {
  const { t, els } = await boot({ storage: { "radar:read": "{oops", "radar:saved": "[[[" } });
  t.setTab("hot"); t.render();
  assert.ok(els["#view"].innerHTML.includes("pytest story 1"));
});

// ------------------------------------------------------------------ actions
test("save, read and mute work and persist", async () => {
  const { t, els, store } = await boot();
  const card = { dataset: { key: "k1" }, querySelector: () => ({ classList: { toggle() {}, contains: () => true } }) };
  click(els, fakeTarget({ act: "save" }, card));
  assert.ok(t.prefs.saved.k1 && JSON.parse(store["radar:saved"]).k1);
  click(els, fakeTarget({ act: "read" }, card));
  assert.ok(t.prefs.read.has("k1"));
  click(els, fakeTarget({ mute: "pytest" }, null));
  t.setTab("hot"); t.render();
  assert.ok(!els["#view"].innerHTML.includes("pytest story 1<"), "muted topic still shown");
  t.setTab("more"); t.render();
  assert.ok(els["#view"].innerHTML.includes("pytest story 1"), "saved items must survive muting");
});

test("course progress cycles To do → Doing → Done → To do", async () => {
  const { t, els } = await boot();
  const id = "https://cCourse";
  for (const expected of ["doing", "done", "todo"]) {
    click(els, fakeTarget({ progress: id }, null));
    assert.equal(t.prefs.progress[id], expected);
  }
});

test("search filters across title, summary, source and tags", async () => {
  const items = [makeItem(1, { title: "Alpha", summary: "about MCP" }), makeItem(2, { title: "Beta" })];
  const { t, els } = await boot({ data: makeData(items) });
  t.setTab("today"); t.setQuery("mcp"); t.render();
  assert.ok(els["#view"].innerHTML.includes("Alpha") && !els["#view"].innerHTML.includes(">Beta<"));
});

test("every tab renders without throwing, also with empty data", async () => {
  for (const data of [makeData(), makeData([], { sources: [], learning: { courses: [] } })]) {
    const { t, els } = await boot({ data });
    for (const tab of ["hot", "today", "topics", "releases", "learn", "more", "unknown-tab"]) {
      t.setTab(tab); t.render();
      assert.ok(typeof els["#view"].innerHTML === "string" && els["#view"].innerHTML.length > 0, tab);
    }
  }
});
