/* Kairoq — client app.
 * 1. shows the last data instantly (from this device), 2. loads fresh data.json,
 * 3. pulls live Hacker News straight from your phone, scoring it with the same rules
 *    the Python collector uses (exported in data.json). Works on GitHub Pages or the server. */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const view = $("#view");
const LIVE_GROUP = "Live · Hacker News";
const QUADS = [
  ["Act now", "act", "Urgent and important for your stack — deal with these first."],
  ["Watch", "watch", "Urgent, but less central to your stack."],
  ["Plan", "plan", "Important, not urgent — read this week."],
  ["FYI", "fyi", "Good to know."],
];
// one consistent line-icon set (24px grid, 1.6 stroke), no emoji
const ICON_PATHS = {
  brief: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  feed: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h5"/>',
  trend: '<path d="M4 17l5-5 4 3 7-8"/><path d="M15 7h5v5"/>',
  tag: '<path d="M3 12V4h8l9 9-8 8-9-9z"/><circle cx="7.5" cy="7.5" r="1.3"/>',
  box: '<path d="M4 7l8-4 8 4v10l-8 4-8-4z"/><path d="M4 7l8 4 8-4M12 11v10"/>',
  learn: '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2 9 2 12 0v-5"/>',
  book: '<path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3z"/><path d="M5 17a3 3 0 013-3h11"/>',
  star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 00-.1-1.2l2-1.6-2-3.4-2.4 1a7 7 0 00-2-1.2L14 3h-4l-.5 2.6a7 7 0 00-2 1.2l-2.4-1-2 3.4 2 1.6a7 7 0 000 2.4l-2 1.6 2 3.4 2.4-1a7 7 0 002 1.2L10 21h4l.5-2.6a7 7 0 002-1.2l2.4 1 2-3.4-2-1.6c.1-.4.1-.8.1-1.2z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  bookmark: '<path d="M6 4h12v17l-6-4-6 4z"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  arrow: '<path d="M7 17L17 7M9 7h8v8"/>',
  chat: '<path d="M4 5h16v11H9l-5 4z"/>',
};
const icon = (n, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON_PATHS[n] || ""}</svg>`;
const NAV = [
  ["hot", "brief", "Briefing"], ["today", "feed", "Feed"], ["trends", "trend", "Trends & terms"],
  ["topics", "tag", "Topics"], ["releases", "box", "Releases"], ["learn", "learn", "Learn (free)"],
  ["library", "book", "Library"], ["saved", "star", "Saved"], ["more", "gear", "Sources & settings"],
];
const TABS = [["hot", "brief", "Brief"], ["today", "feed", "Feed"], ["trends", "trend", "Trends"], ["learn", "learn", "Learn"], ["more", "menu", "More"]];
const FEED_GROUPS = [["all", "All"], ["Releases", "Releases"], ["Official updates", "Official"],
  ["Practitioner blogs", "Blogs"], ["Research", "Research"], ["hn", "Hacker News"], [LIVE_GROUP, "Live"]];

// ---------------------------------------------------------------- storage
const store = {
  get(k, d) { try { const v = localStorage.getItem("radar:" + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("radar:" + k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const prefs = {
  read: new Set(store.get("read", [])),
  saved: store.get("saved", {}),
  muted: new Set(store.get("muted", [])),
  lastVisit: store.get("lastVisit", null),
  progress: store.get("progress", {}),
  theme: store.get("theme", "system"),
  density: store.get("density", "auto"),          // auto = compact on phones, cards elsewhere
  tuning: store.get("tuning", {}),                // {topic: -30..+30} from "More like this / Not for me"
  hidden: new Set(store.get("hidden", [])),
};
const PROTECTED = new Set(["Security", "Breaking change"]);   // never hidden by tuning
const savePrefs = () => {
  store.set("progress", prefs.progress);
  store.set("read", [...prefs.read].slice(-3000));
  store.set("saved", prefs.saved);
  store.set("muted", [...prefs.muted]);
  store.set("theme", prefs.theme);
  store.set("density", prefs.density);
  store.set("tuning", prefs.tuning);
  store.set("hidden", [...prefs.hidden].slice(-2000));
};

let data = window.RADAR_DATA || store.get("cache", null); // RADAR_DATA = offline preview only
let live = [];
let liveState = "idle"; // idle | loading | ok | error
let tab = (location.hash || "#hot").slice(1);
let query = "";
let topicFilter = null;
let todayRange = "new";
let feedGroup = "all";
let learnFilter = "all";
let libKind = "all";
let hotAll = false;
let readerKey = null;
const visitStart = prefs.lastVisit; // items after this are NEW for you

// ---------------------------------------------------------------- helpers
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
const imgUrl = (u) => (/^https:\/\//i.test(u || "") ? u : "");
const rx = (p) => { try { return new RegExp(String(p).replace(/^\(\?i\)/, ""), "i"); } catch { return null; } };
const lvl = (n) => `lvl-${Math.max(0, Math.min(10, Math.round((Number(n) || 0) / 10)))}`;
const ago = (iso) => {
  if (!iso) return "never";
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (!isFinite(m)) return "";
  if (m < 1) return "just now"; if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60); return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
};
const isNew = (it) => {
  if (prefs.read.has(it.key)) return false;
  if (it.group === LIVE_GROUP || !visitStart) return true;
  const found = it.found_at || it.first_seen || "";
  return new Date(found).getTime() > new Date(visitStart).getTime();
};
const qOf = (it) => (QUADS.find(([n]) => n === it.quadrant) || QUADS[3]);

// ------------------------------------------------- scoring (mirror of rank.py)
function tagsFor(it) {
  const text = `${it.title} ${it.summary || ""}`;
  const ex = (data && data.tag_exclude) || {};
  return Object.entries((data && data.tags) || {})
    .filter(([n, p]) => rx(p)?.test(text) && !(ex[n] && rx(ex[n])?.test(text)))
    .map(([n]) => n);
}
function scoreItem(it) {
  const r = data.ranking, text = `${it.title} ${it.summary || ""}`;
  const official = ["Releases", "Official updates"].includes(it.group);
  const stack = r.stack.reduce((s, x) => s + (rx(x.pattern)?.test(text) ? x.weight : 0), 0);
  const when = it.published || it.first_seen;
  const ageH = when ? Math.max(1, (Date.now() - new Date(when).getTime()) / 3.6e6) : 12;
  const velocity = it.points ? Math.min(25, 12 * Math.log10(1 + it.points / ageH)) : 0;
  let importance = Math.min(60, stack) + velocity + Math.min(16, 8 * (it.also_in || []).length) + (official ? r.official_boost : 0);
  const urgentText = r.urgency_title_only_for_news && !official ? it.title : text;
  let reasons = r.urgency.filter((x) => rx(x.pattern)?.test(urgentText)).map((x) => x.label);
  let urgency = Math.max(0, ...r.urgency.filter((x) => reasons.includes(x.label)).map((x) => x.weight));
  if (it.group === "Releases") { urgency = Math.max(urgency, r.release_urgency); if (!reasons.length) reasons = ["New release"]; }
  if (ageH <= r.fresh_hours) urgency += r.fresh_boost;
  if (official && urgency) urgency += r.official_boost;
  importance = Math.round(Math.min(100, importance)); urgency = Math.round(Math.min(100, urgency));
  const quadrant = urgency >= r.act_urgency && importance >= r.act_importance ? "Act now"
    : importance >= r.act_importance ? "Plan" : urgency >= r.act_urgency ? "Watch" : "FYI";
  return { importance, urgency, quadrant, reasons, hot: Math.round(0.55 * importance + 0.45 * urgency) };
}

// ---------------------------------------------------------------- data
async function loadData(force) {
  try {
    const res = await fetch(`data.json?t=${Date.now()}`, { cache: "no-store" });
    if (res.status === 503 && !data) {   // backend is collecting for the very first time
      view.innerHTML = `<p class="empty">Collecting today's news for the first time… this page will update by itself in about a minute.</p>`;
      setTimeout(() => loadData().then(loadLive), 30000);
      return;
    }
    if (!res.ok) throw new Error(res.status);
    data = await res.json();
    store.set("cache", data);
  } catch (e) {
    if (!data) { view.innerHTML = `<p class="empty">Could not load data. Check your connection and tap ↻.</p>`; }
  }
  render();
}

async function loadLive() {
  if (!data) return;
  liveState = "loading"; renderStatus();
  const since = Math.floor(Date.now() / 1000) - 8 * 3600;
  const urls = [
    "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=60",
    `https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=100&numericFilters=created_at_i>${since},points>15`,
  ];
  try {
    const results = await Promise.all(urls.map((u) => fetch(u).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })));
    const known = new Set(data.items.map((i) => i.key));
    const knownTitles = new Set(data.items.map((i) => i.title.toLowerCase()));
    const relevant = rx(data.live.relevant);
    const excludes = data.live.topics.map((t) => t.exclude).filter(Boolean).map(rx).filter(Boolean);
    const seen = new Set();
    live = [];
    for (const hit of results.flatMap((r) => r.hits || [])) {
      const key = `hn:${hit.objectID}`;
      if (!hit.title || seen.has(key) || known.has(key) || knownTitles.has(hit.title.toLowerCase())) continue;
      if (relevant && !relevant.test(hit.title)) continue;
      if (excludes.some((x) => x.test(hit.title))) continue;
      seen.add(key);
      const disc = `https://news.ycombinator.com/item?id=${hit.objectID}`;
      const it = { key, title: hit.title, url: hit.url || disc, source: "Hacker News (live)", group: LIVE_GROUP,
        points: hit.points, comments: hit.num_comments, discussion_url: disc, published: hit.created_at,
        first_seen: data.today, also_in: [], summary: "", summary_kind: "", key_points: [], outline: [], images: [] };
      it.tags = tagsFor(it);
      if (!it.tags.length) continue;
      Object.assign(it, scoreItem(it));
      live.push(it);
    }
    liveState = "ok";
  } catch (e) {
    liveState = "error";
  }
  render();
}

function allItems() {
  if (!data) return [];
  const items = [...data.items, ...live].map((it) => {
    const tags = it.tags && it.tags.length ? it.tags : tagsFor(it);
    const boost = Math.max(-30, Math.min(30, tags.reduce((n, t) => n + (prefs.tuning[t] || 0), 0)));
    const isProtected = (it.reasons || []).some((r) => PROTECTED.has(r));
    const hidden = !isProtected && (prefs.hidden.has(it.key) || boost <= -20);
    return { ...it, tags, base_hot: it.hot, hot: (it.hot || 0) + boost, tuned: boost, hidden, protected: isProtected };
  });
  // muted topics and "Not for me" disappear from every feed (security/breaking items are protected);
  // your Saved list still keeps them
  return items.filter((it) => !it.hidden && (it.protected || !it.tags.some((t) => prefs.muted.has(t))));
}
const findItem = (key) => allItems().find((i) => i.key === key) || [...(data?.items || []), ...live].find((i) => i.key === key) || prefs.saved[key];

function matches(it) {
  if (!query) return true;
  const hay = `${it.title} ${it.summary} ${it.source} ${(it.tags || []).join(" ")} ${(it.terms || []).join(" ")} ${it.group}`.toLowerCase();
  return query.split(/\s+/).every((w) => hay.includes(w));
}
const coursesFor = (tags) => ((data && data.learning && data.learning.courses) || [])
  .filter((c) => c.topics.some((t) => (tags || []).includes(t)));
const glossFor = (terms) => ((data && data.glossary) || []).filter((g) => (terms || []).includes(g.term));

const dense = () => prefs.density === "compact" || (prefs.density === "auto" && typeof window.innerWidth === "number" && window.innerWidth < 700);
const KIND = { ai: ["AI", "AI summary — facts from the article only"], extractive: ["Quoted", "Sentences quoted from the article"], excerpt: ["Excerpt", "Opening lines of the article"] };
const provenance = (it) => it.group === LIVE_GROUP ? ["Live", "Live from Hacker News"] : (KIND[it.summary_kind] || ["Link", "Headline only"]);

function explainItem(it) {
  const r = data.ranking, text = `${it.title} ${it.summary || ""}`;
  const official = ["Releases", "Official updates"].includes(it.group);
  const hits = r.stack.filter((x) => rx(x.pattern)?.test(text)).map((x) => [x.label || "Topic match", x.weight]);
  const when = it.published || it.first_seen;
  const ageH = when ? Math.max(1, (Date.now() - new Date(when).getTime()) / 3.6e6) : 12;
  const velocity = it.points ? Math.min(25, 12 * Math.log10(1 + it.points / ageH)) : 0;
  const rows = [];
  hits.forEach(([l, w]) => rows.push(["Matches your stack", l, `+${w}`]));
  if (hits.reduce((n, [, w]) => n + w, 0) > 60) rows.push(["", "Stack points are capped at 60", ""]);
  if (velocity >= 1) rows.push(["Momentum", `${it.points} votes in ~${Math.round(ageH)} h`, `+${Math.round(velocity)}`]);
  if ((it.also_in || []).length) rows.push(["Seen in several places", it.also_in.slice(0, 3).join(", "), `+${Math.min(16, 8 * it.also_in.length)}`]);
  if (official) rows.push(["Official source", it.group, `+${r.official_boost}`]);
  (it.reasons || []).forEach((x) => rows.push(["Urgency rule", x === "New release" ? "A new version of a tool you use" : `Title mentions: ${x}`, "↑"]));
  if (ageH <= r.fresh_hours) rows.push(["Fresh", "Published in the last 24 h", `+${r.fresh_boost} urgency`]);
  if (it.tuned) rows.push(["Your tuning", it.tuned > 0 ? "You asked for more like this" : "You asked for less like this", `${it.tuned > 0 ? "+" : ""}${it.tuned}`]);
  return rows;
}

// ---------------------------------------------------------------- cards
function card(it, opts = {}) {
  const [, q] = qOf(it);
  const read = prefs.read.has(it.key), saved = !!prefs.saved[it.key];
  const cover = imgUrl(it.cover) || (it.images && it.images[0] && imgUrl(it.images[0].src));
  const when = it.published || it.found_at || it.first_seen;
  const [prov, provTitle] = provenance(it);
  const reason = (it.reasons || [])[0];
  const saveBtn = `<button class="ib" data-act="save" aria-pressed="${saved}" aria-label="${saved ? "Remove from saved" : "Save"}" title="Save">${icon("bookmark", saved ? "fill" : "")}</button>`;
  const openBtn = `<button class="ib go" data-act="reader" aria-label="Open summary" title="Open summary">${icon("arrow")}</button>`;
  if (dense() && !opts.full) {
    return `<article class="card row ${q} ${read ? "read" : ""}" data-key="${esc(it.key)}" tabindex="0" aria-label="${esc(it.title)}">
      <span class="qdot ${q}" title="${esc(it.quadrant || "FYI")}"></span>
      <div class="row-main">
        <a class="t" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener" data-act="open">${esc(it.title)}</a>
        <div class="row-meta"><span class="src">${esc(it.source)}</span><span>${esc(ago(when) || "")}</span>
          <span class="prov" title="${esc(provTitle)}">${esc(prov)}</span>${reason ? `<span class="warn-t">${esc(reason)}</span>` : ""}${isNew(it) ? '<span class="new">NEW</span>' : ""}</div>
      </div>
      <span class="ring ${lvl(it.hot)}" title="Signal score"><b>${esc(it.hot ?? 0)}</b></span>
      ${saveBtn}
    </article>`;
  }
  return `<article class="card ${q} ${read ? "read" : ""}" data-key="${esc(it.key)}" tabindex="0" aria-label="${esc(it.title)}">
    <div class="card-top">
      <span class="qdot ${q}" title="${esc(it.quadrant || "FYI")}"></span>
      <span class="src">${esc(it.source)}</span><span class="sep">·</span><span>${esc(ago(when) || it.first_seen || "")}</span>
      ${it.read_minutes ? `<span class="sep">·</span><span>${esc(it.read_minutes)} min</span>` : ""}
      <span class="prov" title="${esc(provTitle)}">${esc(prov)}</span>
      ${isNew(it) ? '<span class="new">NEW</span>' : ""}
    </div>
    <div class="card-body">
      <div class="card-main">
        <a class="t" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener" data-act="open">${esc(it.title)}</a>
        ${it.summary ? `<p class="sum clamp2">${esc(it.summary)}</p>` : it.group === LIVE_GROUP
          ? '<p class="sum lbl">Live from Hacker News — full summary with the next update.</p>' : ""}
      </div>
      ${cover && !opts.noThumb ? `<img class="thumb" src="${esc(cover)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ""}
    </div>
    <div class="card-foot">
      <span class="ring ${lvl(it.hot)}" title="Signal score: urgency ${esc(it.urgency ?? 0)} · importance ${esc(it.importance ?? 0)}"><b>${esc(it.hot ?? 0)}</b></span>
      <span class="qlabel ${q}">${esc(it.quadrant || "FYI")}</span>
      ${reason ? `<span class="chip warn">${esc(reason)}</span>` : ""}
      ${(it.tags || []).slice(0, 2).map((t) => `<button class="chip" data-tag="${esc(t)}">#${esc(t)}</button>`).join("")}
      ${(it.images || []).length ? `<span class="chip">diagram</span>` : ""}
      <span class="grow"></span>
      ${it.points != null ? `<span class="stat-mini">▲${esc(it.points)}</span>` : ""}
      ${saveBtn}${openBtn}
    </div>
  </article>`;
}
const list = (items, emptyText = "Nothing here.", cls = "") =>
  items.length ? `<div class="grid ${dense() ? "rows" : ""} ${cls}">${items.map((i) => card(i)).join("")}</div>` : `<p class="empty">${esc(emptyText)}</p>`;
const sec = (title, n, cls = "") => `<h2 class="sec ${cls}">${title}${n != null ? ` <span class="count">${esc(n)}</span>` : ""}</h2>`;

function dateMinus(days) {
  const d = new Date((data && data.today) || Date.now()); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------- views
const HOT_LIMIT = 10;
function hash(str) { let h = 0; for (const c of String(str)) h = (h * 31 + c.charCodeAt(0)) | 0; return Math.abs(h); }
function signalMap(items) {
  const r = (data && data.ranking) || { act_importance: 45, act_urgency: 50 };
  const W = 420, H = 230, P = 26;
  const x = (v) => P + (Math.min(100, v || 0) / 100) * (W - 2 * P);
  const y = (v) => H - P - (Math.min(100, v || 0) / 100) * (H - 2 * P);
  const dots = items.slice(0, 60).map((it) => {
    const j = hash(it.key), [, q] = qOf(it);
    const cx = x(it.importance) + ((j % 9) - 4), cy = y(it.urgency) + (((j >> 4) % 9) - 4);
    return `<circle class="d ${q}" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${q === "act" ? 6 : 4.5}" data-open-reader="${esc(it.key)}"><title>${esc(it.title)}</title></circle>`;
  }).join("");
  const qx = x(r.act_importance), qy = y(r.act_urgency);
  return `<svg class="smap" viewBox="0 0 ${W} ${H}" role="img" aria-label="Signal map: urgency versus importance">
    <rect class="zone act" x="${qx}" y="${P}" width="${W - P - qx}" height="${qy - P}" rx="8"/>
    <line class="ax" x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}"/><line class="ax" x1="${P}" y1="${P}" x2="${P}" y2="${H - P}"/>
    <line class="mid" x1="${qx}" y1="${P}" x2="${qx}" y2="${H - P}"/><line class="mid" x1="${P}" y1="${qy}" x2="${W - P}" y2="${qy}"/>
    <text class="zl act" x="${W - P - 6}" y="${P + 14}" text-anchor="end">ACT NOW</text>
    <text class="zl" x="${P + 6}" y="${P + 14}">WATCH</text>
    <text class="zl" x="${W - P - 6}" y="${H - P - 8}" text-anchor="end">PLAN</text>
    <text class="zl" x="${P + 6}" y="${H - P - 8}">FYI</text>
    <text class="axl" x="${W / 2}" y="${H - 6}" text-anchor="middle">importance →</text>
    <text class="axl" x="10" y="${H / 2}" transform="rotate(-90 10 ${H / 2})" text-anchor="middle">urgency →</text>
    ${dots}</svg>`;
}
function renderHot(items) {
  const order = Object.fromEntries(QUADS.map(([n], i) => [n, i]));
  const ranked = items.filter((it) => it.group === LIVE_GROUP || (it.first_seen || "") >= dateMinus(2))
    .sort((a, b) => order[a.quadrant] - order[b.quadrant] || b.hot - a.hot);
  const top = new Set(ranked.slice().sort((a, b) => b.hot - a.hot).slice(0, HOT_LIMIT).map((it) => it.key));
  const shown = hotAll ? ranked : ranked.filter((it) => top.has(it.key));
  const newCount = items.filter(isNew).length;
  const act = ranked.filter((i) => i.quadrant === "Act now").sort((a, b) => b.hot - a.hot);
  const trends = (data.trends || []);
  const okSources = (data.sources || []).filter((s) => s.ok).length;
  const short = (t) => (t.length > 64 ? t.slice(0, 62) + "…" : t);
  const brief = act.length
    ? `<b>${act.length} need${act.length === 1 ? "s" : ""} your attention</b>: ${act.slice(0, 3).map((i) => `<button class="link" data-open-reader="${esc(i.key)}">${esc(short(i.title))}</button>`).join(", ")}${act.length > 3 ? ` and ${act.length - 3} more` : ""}.`
    : "<b>Nothing urgent</b> for your stack right now.";
  const trendTxt = trends.length ? ` Trending: ${trends.slice(0, 3).map((t) => `<button class="link" data-term="${esc(t.term)}">${esc(t.term)}</button>`).join(", ")}.` : "";
  let html = `<section class="hero">
    <div class="hero-grid">
      <div>
        <span class="eyebrow">${esc(newCount)} new · ${esc(new Date().toDateString())}</span>
        <h1>Today's <em>signal</em> for AI&nbsp;+&nbsp;QA</h1>
        <p class="brief">${brief}${trendTxt}</p>
        <div class="stats">
          <button class="stat new" data-goto="today"><b>${newCount}</b><span>new for you</span></button>
          <button class="stat act" data-goto="hot"><b>${act.length}</b><span>act now</span></button>
          <button class="stat" data-goto="trends"><b>${trends.length}</b><span>trending</span></button>
          <button class="stat" data-goto="more"><b>${okSources}/${(data.sources || []).length}</b><span>sources up</span></button>
        </div>
      </div>
      <div class="map-wrap"><div class="map-head"><span>Signal map</span><span class="lbl">tap a dot</span></div>${signalMap(ranked)}</div>
    </div></section>`;
  html += `<div class="sec-row"><h2 class="sec">${hotAll ? "Everything from the last 2 days" : `Top ${HOT_LIMIT} signals`}</h2>`
    + (ranked.length > HOT_LIMIT ? `<button class="btn ghost" data-hotall="1">${hotAll ? `Show top ${HOT_LIMIT} only` : `Show all ${ranked.length}`}</button>` : "") + `</div>`;
  for (const [name, cls, hint] of QUADS) {
    const group = shown.filter((it) => it.quadrant === name);
    if (!group.length) continue;
    html += `<h3 class="qhead ${cls}"><span class="qdot ${cls}"></span>${esc(name)}<span class="count">${group.length}</span><span class="lbl">${esc(hint)}</span></h3>` + list(group, "", name === "Act now" ? "big" : "");
  }
  if (!shown.length) html += `<p class="empty">Nothing hot right now. 🎉</p>`;
  return html;
}

function renderToday(items) {
  const seg = `<div class="seg" role="group" aria-label="Range">
    <button data-range="new" aria-pressed="${todayRange === "new"}">New for you</button>
    <button data-range="week" aria-pressed="${todayRange === "week"}">Last 7 days</button></div>`;
  const groups = `<div class="filterchips">${FEED_GROUPS.map(([g, label]) =>
    `<button data-feedgroup="${esc(g)}" aria-pressed="${feedGroup === g}">${esc(label)}</button>`).join("")}</div>`;
  let pool = todayRange === "new" ? items.filter((it) => isNew(it)) : items;
  if (feedGroup === "hn") pool = pool.filter((it) => it.group.startsWith("HN ·") || it.group.startsWith("Topic ·"));
  else if (feedGroup !== "all") pool = pool.filter((it) => it.group === feedGroup);
  const order = [LIVE_GROUP, ...data.groups];
  let html = seg + groups;
  for (const g of order) {
    const group = pool.filter((it) => it.group === g).sort((a, b) => b.hot - a.hot);
    if (group.length) html += sec(esc(g), group.length) + list(group);
  }
  return pool.length ? html : html + `<p class="empty">You're all caught up. 🎉</p>`;
}

function renderTopics(items) {
  const counts = {};
  data.items.concat(live).forEach((it) => (it.tags || tagsFor(it)).forEach((t) => (counts[t] = (counts[t] || 0) + 1)));
  const chips = Object.keys(data.tags).map((t) =>
    `<button data-topic="${esc(t)}" aria-pressed="${topicFilter === t}" class="${prefs.muted.has(t) ? "muted" : ""}">${esc(t)} ${counts[t] || 0}</button>`).join("");
  let html = sec("🏷️ Topics") + `<div class="filterchips">${chips}</div>`;
  if (!topicFilter) return html + `<p class="empty">Pick a topic.</p>`;
  const muted = prefs.muted.has(topicFilter);
  html += `<button class="btn" data-mute="${esc(topicFilter)}">${muted ? "Unmute" : "Mute"} #${esc(topicFilter)}</button>`;
  const courses = coursesFor([topicFilter]);
  if (courses.length) html += `<p class="hint">🎓 Free to learn: ${courses.map((c) => `<a href="${esc(safeUrl(c.url))}" target="_blank" rel="noopener">${esc(c.title)}</a>`).join(" · ")}</p>`;
  const pool = (muted ? data.items.concat(live) : items).filter((it) => (it.tags || []).includes(topicFilter)).sort((a, b) => b.hot - a.hot);
  return html + list(pool);
}

function renderReleases(items) {
  const rel = items.filter((it) => it.group === "Releases").sort((a, b) => (b.first_seen || "").localeCompare(a.first_seen || ""));
  const off = items.filter((it) => it.group === "Official updates").sort((a, b) => b.hot - a.hot);
  return sec("📦 Releases", rel.length) + list(rel, "No new releases this week.")
    + sec("🏢 Official updates", off.length) + list(off, "No official posts this week.")
    + sec("🔗 Pages without feeds") + `<div class="links">${data.check_pages.map((p) => `<a href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener">${esc(p.name)}</a>`).join("")}</div>`;
}

function termCard(t, compact = false) {
  const g = (data.glossary || []).find((x) => x.term === t.term);
  const def = t.definition || (g && g.def) || "";
  const ex = (t.examples || []).map(findItem).filter(Boolean).slice(0, compact ? 1 : 3);
  return `<div class="term">
    <h3>${t.status ? `<span class="badge ${esc(t.status)}">${esc(t.status)}</span>` : ""}<button class="chip" data-term="${esc(t.term)}">${esc(t.term)}</button>
      ${t.count ? `<span class="lbl">${esc(t.count)} mention${t.count > 1 ? "s" : ""} this week</span>` : ""}</h3>
    ${def ? `<p>${esc(def)}</p>` : `<p class="lbl">New name in the news — tap it to see the stories.</p>`}
    ${ex.length ? `<div class="chips">${ex.map((i) => `<button class="chip" data-open-reader="${esc(i.key)}">↗ ${esc(i.title.slice(0, 60))}</button>`).join("")}</div>` : ""}
  </div>`;
}

function renderTrends() {
  const trends = (data.trends || []).filter((t) => !query || t.term.toLowerCase().includes(query) || (t.definition || "").toLowerCase().includes(query));
  const gloss = (data.glossary || []).filter((g) => !query || `${g.term} ${g.def}`.toLowerCase().includes(query))
    .slice().sort((a, b) => a.term.localeCompare(b.term));
  return sec("📈 Trending terms this week", trends.length)
    + `<p class="hint"><b>New</b> = first seen this week · <b>Rising</b> = mentioned at least twice as often as before. Tap a term to filter the news.</p>`
    + (trends.length ? `<div class="grid">${trends.map((t) => termCard(t)).join("")}</div>` : `<p class="empty">Trends appear after the first few collections.</p>`)
    + sec("📖 Glossary — new & important terms", gloss.length)
    + `<p class="hint">Plain-English definitions of the concepts behind today's news.</p>`
    + `<div class="grid">${gloss.map((g) => termCard({ term: g.term, definition: g.def })).join("")}</div>`;
}

const PROGRESS = ["todo", "doing", "done"];
const PROGRESS_LABEL = { todo: "▶ Start", doing: "⏳ In progress", done: "✓ Done" };
function renderLearn(items) {
  const L = data.learning || { courses: [] };
  const courses = L.courses.filter((c) => !query || `${c.title} ${c.provider} ${c.topics.join(" ")} ${c.why}`.toLowerCase().includes(query))
    .filter((c) => !topicFilter || c.topics.includes(topicFilter))
    .filter((c) => learnFilter === "all" || (prefs.progress[c.url + c.title] || "todo") === learnFilter);
  const done = L.courses.filter((c) => prefs.progress[c.url + c.title] === "done").length;
  const pct = L.courses.length ? Math.round((done / L.courses.length) * 10) : 0;
  const topics = [...new Set(L.courses.flatMap((c) => c.topics))];
  const seg = ["all", ...PROGRESS].map((f) => `<button data-learn="${f}" aria-pressed="${learnFilter === f}">${{ all: "All", todo: "To do", doing: "Doing", done: "Done" }[f]}</button>`).join("");
  const chips = topics.map((t) => `<button data-topic="${esc(t)}" aria-pressed="${topicFilter === t}">${esc(t)}</button>`).join("");
  const cards = courses.map((c) => {
    const id = c.url + c.title, st = prefs.progress[id] || "todo";
    return `<article class="res course ${st === "done" ? "read" : ""}" data-course="${esc(id)}">
      <span class="kind">${esc(c.provider)} · FREE · ${esc(c.cert)}</span>
      <a class="t" href="${esc(safeUrl(c.url))}" target="_blank" rel="noopener">${esc(c.title)}</a>
      <p class="sum">${esc(c.why)}</p>
      <div class="chips"><span class="chip">⏱ ${esc(c.hours)}</span>${c.topics.map((t) => `<span class="chip">#${esc(t)}</span>`).join("")}</div>
      <div class="actions"><button data-progress="${esc(id)}" aria-pressed="${st !== "todo"}">${PROGRESS_LABEL[st]}</button></div>
    </article>`;
  }).join("");
  const found = items.filter((it) => (it.tags || []).includes("Free & learning")).sort((a, b) => b.hot - a.hot).slice(0, 20);
  return sec("🎓 Free courses & certificates", `${done}/${L.courses.length} done`)
    + `<div class="progress"><i class="${lvl(pct * 10)}"></i></div>`
    + `<p class="hint">All free. Certificate rules can change — check the provider page. Last checked ${esc(L.checked || "")}.</p>`
    + `<div class="seg" role="group" aria-label="Progress">${seg}</div><div class="filterchips">${chips}</div>`
    + (cards ? `<div class="grid">${cards}</div>` : '<p class="empty">Nothing matches.</p>')
    + sec("🆓 New free stuff spotted", found.length)
    + `<p class="hint">Free courses, tools, tiers, credits and open-source releases found in today's sources.</p>`
    + list(found, "Nothing new and free spotted this week.");
}

function renderLibrary() {
  const res = (data.resources || []);
  const kinds = ["all", ...new Set(res.map((r) => r.kind))];
  const shown = res.filter((r) => (libKind === "all" || r.kind === libKind)
    && (!query || `${r.name} ${r.about} ${r.topics.join(" ")}`.toLowerCase().includes(query)));
  return sec("📚 Library — the best free resources", shown.length)
    + `<p class="hint">Hand-picked official docs, blogs, newsletters, podcasts, tools and standards for AI + QA.</p>`
    + `<div class="filterchips">${kinds.map((k) => `<button data-libkind="${esc(k)}" aria-pressed="${libKind === k}">${esc(k === "all" ? "All" : k)}</button>`).join("")}</div>`
    + `<div class="grid">${shown.map((r) => `<div class="res"><span class="kind">${esc(r.kind)}</span>
        <a class="t" href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener">${esc(r.name)}</a>
        <p class="sum">${esc(r.about)}</p><div class="chips">${r.topics.map((t) => `<span class="chip">#${esc(t)}</span>`).join("")}</div></div>`).join("")}</div>`;
}

function renderSaved() {
  const items = Object.values(prefs.saved).filter(matches);
  return sec("⭐ Saved", items.length) + list(items, "Tap ☆ on any card to keep it here.");
}

function renderMore() {
  const ok = data.sources.filter((s) => s.ok).length;
  const rows = data.sources.map((s) => `<tr><td>${esc(s.name)}<br><span class="lbl">${esc(s.group)}</span></td>
    <td class="${s.ok ? "ok" : "bad"}">${s.ok ? "✓ " + esc(s.count) : "✗"}</td><td class="lbl">${esc(s.error || "")}</td></tr>`).join("");
  const tiles = [["topics", "🏷️", "Topics", "Filter or mute"], ["releases", "📦", "Releases", "Versions & vendor news"],
    ["library", "📚", "Library", "Best free resources"], ["saved", "⭐", "Saved", `${Object.keys(prefs.saved).length} cards`]];
  return `<div class="tiles mobile-only">${tiles.map(([t, i, n, s]) => `<button class="tile" data-goto="${t}"><span class="ico">${i}</span><b>${n}</b><span>${esc(s)}</span></button>`).join("")}</div>`
    + sec("⚙️ Settings")
    + `<p class="hint">Theme: ${esc(prefs.theme)} · Muted topics: ${prefs.muted.size ? [...prefs.muted].map(esc).join(", ") : "none"} · Read: ${prefs.read.size} · Saved: ${Object.keys(prefs.saved).length}</p>`
    + `<p class="hint">View: ${dense() ? "compact list" : "cards"} · Tuned topics: ${Object.entries(prefs.tuning).filter(([, v]) => v).map(([k, v]) => `${esc(k)} ${v > 0 ? "+" : ""}${v}`).join(", ") || "none"} · Hidden stories: ${prefs.hidden.size}</p>`
    + `<button class="btn" data-act="theme">◐ Switch theme</button><button class="btn" data-act="density">☰ Compact / cards</button><button class="btn" data-setting="reset-tuning">Reset my tuning</button><button class="btn" data-setting="unmute">Unmute all</button>`
    + `<button class="btn" data-setting="clear-read">Clear read history</button><button class="btn" data-setting="export">Export my data</button>`
    + `<label class="btn">Import<input type="file" accept="application/json" data-setting="import" hidden></label>`
    + sec("🧠 Summaries")
    + `<p class="hint">${data.summaries === "ai" ? "AI summaries are on (they only use facts from the article)." : "Summaries are <b>quoted</b> from each article — the most informative sentences, key points per section and the outline — so nothing is invented. Add an ANTHROPIC_API_KEY (or OpenAI) secret in GitHub for rewritten plain-English summaries."}</p>`
    + sec("📡 Sources", `${ok}/${data.sources.length} working`)
    + `<p class="hint">Collected ${esc(ago(data.generated))}. Live Hacker News: ${esc(liveState)}.</p>`
    + `<table><thead><tr><th>Source</th><th>Items</th><th>Note</th></tr></thead><tbody>${rows}</tbody></table>`;
}

// ---------------------------------------------------------------- reader
function readerHtml(it) {
  const [, q] = qOf(it);
  const kindLabel = { ai: "AI summary — written only from the article's facts", extractive: "Quoted summary — the article's own most informative sentences, in order", excerpt: "Excerpt from the article" }[it.summary_kind] || "";
  const figures = (it.images || []).filter((im) => imgUrl(im.src)).map((im) =>
    `<figure><a href="${esc(im.src)}" target="_blank" rel="noopener"><img src="${esc(im.src)}" alt="${esc(im.alt)}" loading="lazy" referrerpolicy="no-referrer"></a><figcaption>${esc(im.alt)} · from the article</figcaption></figure>`).join("");
  const terms = glossFor(it.terms);
  const courses = coursesFor(it.tags).slice(0, 4);
  const points = (it.key_points || []).map((k) => `<li>${k.heading ? `<b>${esc(k.heading)}</b>` : ""}${esc(k.point)}</li>`).join("");
  return `<div class="reader-head"><button class="icon-btn" data-act="close-reader" aria-label="Close">✕</button>
      <div class="grow">${esc(it.source)}${it.read_minutes ? ` · ${esc(it.read_minutes)} min article` : ""}</div>
      <button class="icon-btn" data-act="save" data-key="${esc(it.key)}" aria-pressed="${!!prefs.saved[it.key]}" aria-label="Save">${prefs.saved[it.key] ? "★" : "☆"}</button></div>
    <div class="reader-body" data-key="${esc(it.key)}">
      <div class="chips"><span class="pill ${q}">${esc(it.quadrant || "FYI")}</span>${(it.reasons || []).map((r) => `<span class="chip">⚠ ${esc(r)}</span>`).join("")}${(it.tags || []).map((t) => `<span class="chip">#${esc(t)}</span>`).join("")}</div>
      <h1>${esc(it.title)}</h1>
      <div class="meters"><div class="meter u">Urgency <b>${esc(it.urgency ?? 0)}</b><div class="bar"><i class="${lvl(it.urgency)}"></i></div></div>
        <div class="meter">Importance <b>${esc(it.importance ?? 0)}</b><div class="bar"><i class="${lvl(it.importance)}"></i></div></div></div>
      ${imgUrl(it.cover) && !figures ? `<img class="cover" src="${esc(it.cover)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ""}
      <h4>Summary <span class="prov">${esc(provenance(it)[0])}</span></h4>
      ${it.summary ? `<p class="lead">${esc(it.summary)}</p><div class="kind">ⓘ ${esc(kindLabel)}</div>` : `<p class="notice">${esc(it.no_text_reason || (it.group === LIVE_GROUP ? "Live from Hacker News — the full briefing arrives with the next update (within 30 minutes)." : "No summary yet — the full briefing is added on the next update."))}</p>`}
      ${points ? `<h4>Key points, section by section</h4><ol class="points">${points}</ol>` : ""}
      ${(it.discussion || []).length ? `<h4>From the discussion <span class="prov">Quoted</span></h4>${it.discussion.map((q) => `<blockquote class="quote">${esc(q)}</blockquote>`).join("")}<p class="lbl">Comments from Hacker News readers — opinions, not facts.</p>` : ""}
      ${(it.outline || []).length ? `<h4>What the article covers</h4><div class="outline">${it.outline.map((h) => `<span>${esc(h)}</span>`).join("")}</div>` : ""}
      ${figures ? `<section class="figs"><h4>Diagrams & architecture from the article</h4>${figures}</section>` : ""}
      ${terms.length ? `<h4>Terms explained</h4><div class="grid one">${terms.map((g) => `<div class="term"><h3>${esc(g.term)}</h3><p>${esc(g.def)}</p></div>`).join("")}</div>` : ""}
      ${courses.length ? `<h4>Learn this for free</h4><div class="grid one">${courses.map((c) => `<div class="res"><span class="kind">${esc(c.provider)} · ${esc(c.cert)}</span><a class="t" href="${esc(safeUrl(c.url))}" target="_blank" rel="noopener">${esc(c.title)}</a></div>`).join("")}</div>` : ""}
      ${data && data.ranking ? `<h4>Why it's ranked here</h4><div class="why"><table>${explainItem(it).map(([a, b, c]) => `<tr><td>${esc(a)}</td><td>${esc(b)}</td><td class="pts">${esc(c)}</td></tr>`).join("")}
        <tr class="tot"><td>Result</td><td>Urgency ${esc(it.urgency ?? 0)} · Importance ${esc(it.importance ?? 0)} → ${esc(it.quadrant || "FYI")}</td><td class="pts">${esc(it.hot ?? 0)}</td></tr></table></div>
      <div class="tune"><span class="lbl">Teach the ranking:</span>
        <button class="btn ghost" data-act="tune-more" data-key="${esc(it.key)}">👍 More like this</button>
        <button class="btn ghost" data-act="tune-less" data-key="${esc(it.key)}">👎 Not for me</button>
        <button class="btn ghost" data-act="read" data-key="${esc(it.key)}">${prefs.read.has(it.key) ? "Mark unread" : "Mark read"}</button></div>
      ${it.protected ? '<p class="notice">Security and breaking-change stories are always shown, even if you tune them down.</p>' : ""}` : ""}
      <h4>Go deeper</h4>
      <div class="actions"><a class="primary" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener" data-act="open" data-key="${esc(it.key)}">Read the original ↗</a>
        ${it.discussion_url && it.discussion_url !== it.url ? `<a href="${esc(safeUrl(it.discussion_url))}" target="_blank" rel="noopener">💬 Discussion${it.comments != null ? ` (${esc(it.comments)})` : ""}</a>` : ""}
        ${(it.also_in || []).length ? `<span class="lbl">Also in: ${esc(it.also_in.join(", "))}</span>` : ""}</div>
      <p class="notice">Always check the original before acting on anything important.</p>
    </div>`;
}
function openReader(key) {
  const it = findItem(key);
  const el = $("#reader"), bd = $("#reader-backdrop");
  if (!it || !el) return;
  readerKey = key;
  if (!prefs.read.has(key)) { prefs.read.add(key); savePrefs(); }   // opening = read
  el.innerHTML = readerHtml(it);
  el.hidden = false; if (bd) bd.hidden = false;
  document.body && document.body.classList && document.body.classList.add("lock");
  el.scrollTop = 0;
}
function closeReader() {
  const el = $("#reader"), bd = $("#reader-backdrop");
  readerKey = null;
  if (el) el.hidden = true; if (bd) bd.hidden = true;
  document.body && document.body.classList && document.body.classList.remove("lock");
}

// ---------------------------------------------------------------- rail + nav + status
function renderRail() {
  const rail = $("#rail");
  if (!rail || !data) return;
  const trends = (data.trends || []).slice(0, 6);
  const topTags = {};
  allItems().filter((i) => i.quadrant !== "FYI").forEach((i) => (i.tags || []).forEach((t) => (topTags[t] = (topTags[t] || 0) + 1)));
  const tagOrder = Object.keys(topTags).sort((a, b) => topTags[b] - topTags[a]);
  const courses = coursesFor(tagOrder.slice(0, 4)).filter((c) => (prefs.progress[c.url + c.title] || "todo") !== "done").slice(0, 3);
  rail.innerHTML = `<section><h3>Trending this week</h3>${trends.length ? trends.map((t) => termCard(t, true)).join("") : '<p class="lbl">Trends appear after a few collections.</p>'}</section>
    <section><h3>Learn next — free</h3>${courses.map((c) => `<div class="term"><h3><a href="${esc(safeUrl(c.url))}" target="_blank" rel="noopener">${esc(c.title)}</a></h3><p>${esc(c.why)}</p></div>`).join("") || '<p class="lbl">You are up to date.</p>'}</section>`;
}
function renderNav() {
  const counts = data ? { today: allItems().filter(isNew).length, saved: Object.keys(prefs.saved).length,
    trends: (data.trends || []).length } : {};
  const side = $("#sidenav"), chips = $("#chipnav");
  if (side) side.innerHTML = NAV.map(([t, i, n]) => `<button data-tab="${t}" aria-current="${t === tab ? "page" : "false"}">${icon(i)}<span>${esc(n)}</span>${counts[t] ? `<span class="n">${esc(counts[t])}</span>` : ""}</button>`).join("");
  if (chips) chips.innerHTML = NAV.map(([t, i, n]) => `<button data-tab="${t}" aria-current="${t === tab ? "page" : "false"}">${icon(i)}${esc(n)}</button>`).join("");
  const tabsEl = $("#tabs");
  if (tabsEl) tabsEl.innerHTML = TABS.map(([t, i, n]) => `<button data-tab="${t}" aria-current="${t === tab || (t === "more" && !TABS.some(([x]) => x === tab)) ? "page" : "false"}">${icon(i)}<span>${esc(n)}</span></button>`).join("");
}
function renderStatus() {
  if (!data) return;
  const failed = data.sources.filter((s) => !s.ok).length;
  const liveTxt = { idle: "", loading: '<span class="sp"><i class="pulse"></i>connecting live</span>', ok: `<span class="sp ok"><i class="pulse"></i>Live +${live.length}</span>`, error: '<span class="sp warn">live HN unavailable</span>' }[liveState];
  const html = `<span class="sp">Updated ${esc(ago(data.generated))}</span>${liveTxt}${failed ? `<span class="sp warn">${failed} source(s) failed</span>` : ""}`;
  $("#status").innerHTML = html;
  const side = $("#side-status"); if (side) side.innerHTML = html;
  $("#refresh").classList.toggle("spin", liveState === "loading");
}
function applyTheme() {
  const root = document.documentElement;
  if (!root) return;
  if (prefs.theme === "system") delete root.dataset.theme; else root.dataset.theme = prefs.theme;
}

function render() {
  renderStatus();
  if (!data) return;
  renderNav();
  const items = allItems().filter(matches);
  const views = { hot: renderHot, today: renderToday, topics: renderTopics, releases: renderReleases, trends: renderTrends,
    learn: renderLearn, library: renderLibrary, saved: renderSaved, more: renderMore };
  view.innerHTML = (views[tab] || renderHot)(items);
  renderRail();
}

// ---------------------------------------------------------------- events
function go(t) { tab = t; history.replaceState(null, "", "#" + tab); render(); window.scrollTo && window.scrollTo(0, 0); }

function onClick(e) {
  const el = e.target.closest("[data-act],[data-tag],[data-topic],[data-mute],[data-range],[data-setting],[data-learn],[data-progress],[data-hotall],[data-tab],[data-goto],[data-term],[data-feedgroup],[data-libkind],[data-open-reader]");
  if (!el) {
    const c = e.target.closest && e.target.closest(".card");
    if (c && c.dataset && c.dataset.key) openReader(c.dataset.key);
    return;
  }
  const d = el.dataset;
  if (d.tab) { e.preventDefault(); go(d.tab); return; }
  if (d.goto) { go(d.goto); return; }
  if (d.hotall) { hotAll = !hotAll; render(); return; }
  if (d.learn) { learnFilter = d.learn; render(); return; }
  if (d.feedgroup) { feedGroup = d.feedgroup; render(); return; }
  if (d.libkind) { libKind = d.libkind; render(); return; }
  if (d.openReader) { openReader(d.openReader); return; }
  if (d.term) { closeReader(); query = d.term.toLowerCase().replace(/\s*\(.*\)$/, ""); const s = $("#search"); if (s) s.value = query; go("today"); todayRange = "week"; render(); return; }
  if (d.progress) {
    const cur = prefs.progress[d.progress] || "todo";
    prefs.progress[d.progress] = PROGRESS[(PROGRESS.indexOf(cur) + 1) % PROGRESS.length];
    savePrefs(); render(); return;
  }
  if (d.act === "density") { prefs.density = dense() ? "comfortable" : "compact"; savePrefs(); render(); return; }
  if ((d.act === "tune-more" || d.act === "tune-less") && d.key) {
    const it = findItem(d.key); const step = d.act === "tune-more" ? 10 : -10;
    (it && it.tags || []).slice(0, 3).forEach((t) => { prefs.tuning[t] = Math.max(-30, Math.min(30, (prefs.tuning[t] || 0) + step)); });
    if (step < 0 && it && !(it.reasons || []).some((r) => PROTECTED.has(r))) { prefs.hidden.add(d.key); closeReader(); }
    savePrefs(); render(); if (readerKey) openReader(readerKey); return;
  }
  if (d.setting === "reset-tuning") { prefs.tuning = {}; prefs.hidden.clear(); savePrefs(); render(); return; }
  if (d.act === "theme") { prefs.theme = { system: "light", light: "dark", dark: "system" }[prefs.theme] || "system"; applyTheme(); savePrefs(); render(); return; }
  if (d.act === "close-reader") { closeReader(); return; }
  const cardEl = el.closest(".card") || el.closest(".reader-body");
  const key = d.key || (cardEl && cardEl.dataset.key);
  const item = key && findItem(key);
  if (d.act === "open" && key) { prefs.read.add(key); savePrefs(); setTimeout(render, 300); return; }
  e.preventDefault();
  if (d.act === "reader" && key) { openReader(key); return; }
  if (d.act === "save" && item) { prefs.saved[key] ? delete prefs.saved[key] : (prefs.saved[key] = item); }
  if (d.act === "read" && key) { prefs.read.has(key) ? prefs.read.delete(key) : prefs.read.add(key); }
  if (d.tag) { closeReader(); tab = "topics"; topicFilter = d.tag; history.replaceState(null, "", "#topics"); }
  if (d.topic) { topicFilter = topicFilter === d.topic ? null : d.topic; }
  if (d.mute) { const t = d.mute; prefs.muted.has(t) ? prefs.muted.delete(t) : prefs.muted.add(t); }
  if (d.range) { todayRange = d.range; }
  if (d.setting === "unmute") prefs.muted.clear();
  if (d.setting === "clear-read" && confirm("Clear read history?")) prefs.read.clear();
  if (d.setting === "export") {
    const blob = new Blob([JSON.stringify({ read: [...prefs.read], saved: prefs.saved, muted: [...prefs.muted], progress: prefs.progress })], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "radar-prefs.json" }); a.click();
  }
  savePrefs(); render();
  if (readerKey && (d.act === "save" || d.act === "read")) openReader(readerKey);
}
view.addEventListener("click", onClick);
for (const sel of ["#rail", "#reader", ".sidebar", "#chipnav", "#tabs", ".topbar"]) {
  const el = $(sel);
  if (el && el !== view) el.addEventListener("click", onClick);
}
const backdrop = $("#reader-backdrop");
if (backdrop) backdrop.addEventListener("click", closeReader);

view.addEventListener("change", async (e) => {
  if (e.target.dataset.setting !== "import" || !e.target.files[0]) return;
  try {
    const d = JSON.parse(await e.target.files[0].text());
    (d.read || []).forEach((k) => prefs.read.add(k)); Object.assign(prefs.saved, d.saved || {}); (d.muted || []).forEach((t) => prefs.muted.add(t));
    Object.assign(prefs.progress, d.progress || {});
    savePrefs(); render();
  } catch { alert("That file is not a Kairoq export."); }
});
let searchTimer;
$("#search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { query = e.target.value.trim().toLowerCase(); render(); }, 150);
});
// GitHub Pages / Cloudflare Pages are static: there is no /api there, so don't call it
// (it only produced a red 405 in the console). The Python server has the API.
const STATIC_HOST = /\.github\.io$|\.pages\.dev$/i.test((typeof location !== "undefined" && location.hostname) || "");
$("#refresh").addEventListener("click", async () => {
  // With the backend server this starts a full refresh of every source; on static hosting
  // the button reloads data.json + live Hacker News.
  if (!STATIC_HOST) try {
    const res = await fetch("api/refresh", { method: "POST" });
    if (res.status === 202) setTimeout(() => loadData().then(loadLive), 25000);
  } catch { /* static hosting or offline */ }
  loadData(true).then(loadLive);
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target && e.target.classList && e.target.classList.contains("card")) openReader(e.target.dataset.key);
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); $("#search").focus(); }
  if (e.key === "Escape" && readerKey) closeReader();
  if (e.key === "/" && document.activeElement !== $("#search")) { e.preventDefault(); $("#search").focus(); }
});
// broken remote images (diagram/cover) are removed instead of showing an empty box
document.addEventListener("error", (e) => {
  const t = e.target;
  if (t && t.tagName === "IMG" && t.closest) {
    const box = t.closest("figure") || t, figs = t.closest(".figs");
    box.remove();
    if (figs && !figs.querySelector("figure")) figs.remove();   // no empty "Diagrams" heading
  }
}, true);
// refresh whenever the app comes back to the foreground (e.g. reopened from home screen)
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") store.set("lastVisit", new Date().toISOString());
  if (document.visibilityState === "visible" && data && Date.now() - new Date(data.generated).getTime() > 5 * 60000) loadData().then(loadLive);
});
window.addEventListener("pagehide", () => store.set("lastVisit", new Date().toISOString()));
// Service worker: always check for a new version, and when a new one takes over, reload once
// so a phone/browser never keeps running an old app.js with a new page (mixed old/new layout).
if (typeof navigator !== "undefined" && "serviceWorker" in navigator) {
  const hadController = !!navigator.serviceWorker.controller;
  let reloaded = false;
  navigator.serviceWorker.register("sw.js", { updateViaCache: "none" }).then((reg) => reg.update && reg.update()).catch(() => {});
  navigator.serviceWorker.addEventListener && navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (hadController && !reloaded) { reloaded = true; location.reload(); }
  });
}

// ---------------------------------------------------------------- start
applyTheme();
render();                       // 1. instant: last data on this device
loadData().then(loadLive);      // 2. fresh data.json, 3. live Hacker News
setInterval(renderStatus, 60000);
