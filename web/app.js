/* AI + QA Radar — client app.
 * 1. shows the last data instantly (from this device), 2. loads fresh data.json,
 * 3. pulls live Hacker News straight from your phone, scoring it with the same rules
 *    the Python collector uses (exported in data.json). No server needed. */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const view = $("#view");
const LIVE_GROUP = "Live · Hacker News";
const QUADS = [
  ["Act now", "act", "Urgent and important for your stack: deal with these first."],
  ["Watch", "watch", "Urgent, less central to your stack: keep an eye on them."],
  ["Plan", "plan", "Important, not urgent: read when you have time this week."],
  ["FYI", "fyi", "Good to know."],
];

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
};
const savePrefs = () => {
  store.set("progress", prefs.progress);
  store.set("read", [...prefs.read].slice(-3000));
  store.set("saved", prefs.saved);
  store.set("muted", [...prefs.muted]);
};

let data = window.RADAR_DATA || store.get("cache", null); // RADAR_DATA = offline preview only
let live = [];
let liveState = "idle"; // idle | loading | ok | error
let tab = (location.hash || "#hot").slice(1);
let query = "";
let topicFilter = null;
let todayRange = "new";
let learnFilter = "all";
let hotAll = false;
const visitStart = prefs.lastVisit; // items after this are NEW for you

// ---------------------------------------------------------------- helpers
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
const rx = (p) => { try { return new RegExp(String(p).replace(/^\(\?i\)/, ""), "i"); } catch { return null; } };
const ago = (iso) => {
  if (!iso) return "never";
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 1) return "just now"; if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60); return h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`;
};
// NEW = collected after your previous visit (or live right now), and not read yet
const isNew = (it) => {
  if (prefs.read.has(it.key)) return false;
  if (it.group === LIVE_GROUP || !visitStart) return true;
  const found = it.found_at || it.first_seen || "";
  return new Date(found).getTime() > new Date(visitStart).getTime();
};

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
  let reasons = r.urgency.filter((x) => rx(x.pattern)?.test(text)).map((x) => x.label);
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
        first_seen: data.today, also_in: [], summary: "", summary_kind: "" };
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
  const items = [...data.items, ...live].map((it) => ({ ...it, tags: it.tags && it.tags.length ? it.tags : tagsFor(it) }));
  // muted topics disappear from every feed; your Saved list (renderSaved) still keeps them
  return items.filter((it) => !it.tags.some((t) => prefs.muted.has(t)));
}

function matches(it) {
  if (!query) return true;
  const hay = `${it.title} ${it.summary} ${it.source} ${(it.tags || []).join(" ")} ${it.group}`.toLowerCase();
  return query.split(/\s+/).every((w) => hay.includes(w));
}

// ---------------------------------------------------------------- render
function card(it) {
  const q = (QUADS.find(([n]) => n === it.quadrant) || QUADS[3])[1];
  const read = prefs.read.has(it.key), saved = !!prefs.saved[it.key];
  const disc = it.discussion_url && it.discussion_url !== it.url
    ? `<a href="${esc(safeUrl(it.discussion_url))}" target="_blank" rel="noopener">${it.comments != null ? esc(it.comments) + " comments" : "discuss"}</a>` : "";
  const summary = it.summary
    ? `<p class="sum clamp">${it.summary_kind === "ai" ? "" : '<span class="lbl">Excerpt · </span>'}${esc(it.summary)}</p>
       ${it.summary.split(/\s+/).length > 45 ? '<button class="more" data-act="more">Show more</button>' : ""}`
    : `<p class="sum lbl">${it.group === LIVE_GROUP ? "Live from Hacker News; summary comes with the next update." : "No summary available — open the original."}</p>`;
  return `<article class="card ${q} ${read ? "read" : ""}" data-key="${esc(it.key)}">
    <a class="t" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener" data-act="open">${esc(it.title)}</a>
    <div class="badges">
      ${isNew(it) && !read ? '<span class="chip new">NEW</span>' : ""}
      <span class="chip q ${q}">${esc(it.quadrant)}</span>
      ${(it.reasons || []).map((r) => `<span class="chip">${esc(r)}</span>`).join("")}
      ${(it.tags || []).slice(0, 3).map((t) => `<button class="chip" data-tag="${esc(t)}">#${esc(t)}</button>`).join("")}
    </div>
    <div class="meter"><span>Urgency <b>${esc(it.urgency)}</b></span><span>Importance <b>${esc(it.importance)}</b></span></div>
    ${summary}
    <div class="meta"><span>${esc(it.source)}</span>${it.points != null ? `<span>▲ ${esc(it.points)}</span>` : ""}${disc}
      ${(it.also_in || []).length ? `<span>also in: ${esc(it.also_in.join(", "))}</span>` : ""}
      <span>${esc(it.first_seen || "")}</span></div>
    <div class="actions">
      <button data-act="save" aria-pressed="${saved}">${saved ? "★ Saved" : "☆ Save"}</button>
      <button data-act="read" aria-pressed="${read}">${read ? "✓ Read" : "Mark read"}</button>
    </div>
  </article>`;
}

const list = (items, emptyText = "Nothing here.") =>
  items.length ? items.map(card).join("") : `<p class="empty">${esc(emptyText)}</p>`;

const HOT_LIMIT = 10;
function renderHot(items) {
  const order = Object.fromEntries(QUADS.map(([n], i) => [n, i]));
  const ranked = items.filter((it) => it.group === LIVE_GROUP || (it.first_seen || "") >= dateMinus(2))
    .sort((a, b) => order[a.quadrant] - order[b.quadrant] || b.hot - a.hot);
  // the top 10 = the 10 most urgent/important, still grouped by box
  const top = new Set(ranked.slice().sort((a, b) => b.hot - a.hot).slice(0, HOT_LIMIT).map((it) => it.key));
  const shown = hotAll ? ranked : ranked.filter((it) => top.has(it.key));
  let html = `<p class="hint">${hotAll ? "Everything from the last 2 days" : `Your top ${HOT_LIMIT}`}, ranked by urgency × importance for your stack.</p>`;
  for (const [name, cls, hint] of QUADS) {
    const group = shown.filter((it) => it.quadrant === name);
    if (!group.length) continue;
    html += `<h2 class="q-${cls}">${esc(name)} <span class="count">${group.length}</span></h2><p class="hint">${esc(hint)}</p>${list(group)}`;
  }
  if (!shown.length) html += `<p class="empty">Nothing hot right now. 🎉</p>`;
  if (ranked.length > HOT_LIMIT) {
    html += `<button class="btn" data-hotall="1">${hotAll ? `Show top ${HOT_LIMIT} only` : `Show all ${ranked.length}`}</button>`;
  }
  return html;
}

function dateMinus(days) {
  const d = new Date((data && data.today) || Date.now()); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10);
}

function renderToday(items) {
  const seg = `<div class="seg" role="group" aria-label="Range">
    <button data-range="new" aria-pressed="${todayRange === "new"}">New for you</button>
    <button data-range="week" aria-pressed="${todayRange === "week"}">Last 7 days</button></div>`;
  const pool = todayRange === "new" ? items.filter((it) => isNew(it) && !prefs.read.has(it.key)) : items;
  const order = [LIVE_GROUP, ...data.groups];
  let html = seg;
  for (const g of order) {
    const group = pool.filter((it) => it.group === g).sort((a, b) => b.hot - a.hot);
    if (group.length) html += `<h2>${esc(g)} <span class="count">${group.length}</span></h2>${list(group)}`;
  }
  return pool.length ? html : seg + `<p class="empty">You're all caught up. 🎉</p>`;
}

function renderTopics(items) {
  const counts = {};
  data.items.concat(live).forEach((it) => (it.tags || tagsFor(it)).forEach((t) => (counts[t] = (counts[t] || 0) + 1)));
  const chips = Object.keys(data.tags).map((t) =>
    `<button data-topic="${esc(t)}" aria-pressed="${topicFilter === t}" class="${prefs.muted.has(t) ? "muted" : ""}">${esc(t)} ${counts[t] || 0}</button>`).join("");
  let html = `<div class="chips">${chips}</div>`;
  if (!topicFilter) return html + `<p class="empty">Pick a topic.</p>`;
  const muted = prefs.muted.has(topicFilter);
  html += `<button class="btn" data-mute="${esc(topicFilter)}">${muted ? "Unmute" : "Mute"} #${esc(topicFilter)}</button>`;
  const pool = (muted ? data.items.concat(live) : items).filter((it) => (it.tags || []).includes(topicFilter)).sort((a, b) => b.hot - a.hot);
  return html + list(pool);
}

function renderReleases(items) {
  const rel = items.filter((it) => it.group === "Releases").sort((a, b) => (b.first_seen || "").localeCompare(a.first_seen || ""));
  const off = items.filter((it) => it.group === "Official updates").sort((a, b) => b.hot - a.hot);
  return `<h2>📦 Releases <span class="count">${rel.length}</span></h2>${list(rel, "No new releases this week.")}
    <h2>🏢 Official updates <span class="count">${off.length}</span></h2>${list(off, "No official posts this week.")}
    <h2>🔗 Pages without feeds</h2><div class="links">${data.check_pages.map((p) => `<a href="${esc(safeUrl(p.url))}" target="_blank" rel="noopener">${esc(p.name)}</a>`).join("")}</div>`;
}

function renderSaved() {
  const items = Object.values(prefs.saved).filter(matches);
  return `<h2>⭐ Saved <span class="count">${items.length}</span></h2>` + list(items, "Tap ☆ Save on any card to keep it here.");
}

const PROGRESS = ["todo", "doing", "done"];
const PROGRESS_LABEL = { todo: "▶ Start", doing: "⏳ In progress", done: "✓ Done" };
function renderLearn(items) {
  const L = data.learning || { courses: [] };
  const courses = L.courses.filter((c) => !query || `${c.title} ${c.provider} ${c.topics.join(" ")} ${c.why}`.toLowerCase().includes(query))
    .filter((c) => !topicFilter || c.topics.includes(topicFilter))
    .filter((c) => learnFilter === "all" || (prefs.progress[c.url + c.title] || "todo") === learnFilter);
  const done = L.courses.filter((c) => prefs.progress[c.url + c.title] === "done").length;
  const topics = [...new Set(L.courses.flatMap((c) => c.topics))];
  const seg = ["all", ...PROGRESS].map((f) => `<button data-learn="${f}" aria-pressed="${learnFilter === f}">${{ all: "All", todo: "To do", doing: "Doing", done: "Done" }[f]}</button>`).join("");
  const chips = topics.map((t) => `<button data-topic="${esc(t)}" aria-pressed="${topicFilter === t}">${esc(t)}</button>`).join("");
  const cards = courses.map((c) => {
    const id = c.url + c.title, st = prefs.progress[id] || "todo";
    return `<article class="card ${st === "done" ? "read" : ""}" data-course="${esc(id)}">
      <a class="t" href="${esc(safeUrl(c.url))}" target="_blank" rel="noopener">${esc(c.title)}</a>
      <div class="badges"><span class="chip q plan">FREE</span><span class="chip">${esc(c.cert)}</span><span class="chip">${esc(c.hours)}</span>
        ${c.topics.map((t) => `<span class="chip">#${esc(t)}</span>`).join("")}</div>
      <p class="sum">${esc(c.why)}</p>
      <div class="meta"><span>${esc(c.provider)}</span></div>
      <div class="actions"><button data-progress="${esc(id)}" aria-pressed="${st !== "todo"}">${PROGRESS_LABEL[st]}</button></div>
    </article>`;
  }).join("");
  const found = items.filter((it) => (it.tags || []).includes("Free & learning")).sort((a, b) => b.hot - a.hot).slice(0, 20);
  return `<h2>🎓 Free courses & certificates <span class="count">${done}/${L.courses.length} done</span></h2>
    <p class="hint">All free. Certificate rules can change — check the provider page. Last checked ${esc(L.checked || "")}.</p>
    <div class="seg" role="group" aria-label="Progress">${seg}</div><div class="chips">${chips}</div>
    ${cards || '<p class="empty">Nothing matches.</p>'}
    <h2>🆓 New free stuff spotted <span class="count">${found.length}</span></h2>
    <p class="hint">Free courses, tools, tiers, credits and open-source releases found in today's sources.</p>
    ${list(found, "Nothing new and free spotted this week.")}`;
}

function renderMore() {
  const ok = data.sources.filter((s) => s.ok).length;
  const rows = data.sources.map((s) => `<tr><td>${esc(s.name)}<br><span class="lbl">${esc(s.group)}</span></td>
    <td class="${s.ok ? "ok" : "bad"}">${s.ok ? "✓ " + esc(s.count) : "✗"}</td><td class="lbl">${esc(s.error || "")}</td></tr>`).join("");
  return `${renderSaved()}<h2>⚙️ Settings</h2>
    <p class="hint">Muted topics: ${prefs.muted.size ? [...prefs.muted].map(esc).join(", ") : "none"} · Read: ${prefs.read.size} · Saved: ${Object.keys(prefs.saved).length}</p>
    <button class="btn" data-setting="unmute">Unmute all</button>
    <button class="btn" data-setting="clear-read">Clear read history</button>
    <button class="btn" data-setting="export">Export my data</button>
    <label class="btn">Import<input type="file" accept="application/json" data-setting="import" hidden></label>
    <h2>🧠 Summaries</h2>
    <p class="hint">${data.summaries === "ai" ? "AI summaries are on." : "Showing article excerpts. Add an ANTHROPIC_API_KEY (or OpenAI key) secret in GitHub to switch on plain-English AI summaries."}</p>
    <h2>📡 Sources <span class="count">${ok}/${data.sources.length} working</span></h2>
    <p class="hint">Collected ${esc(ago(data.generated))}. Live Hacker News: ${esc(liveState)}.</p>
    <table><thead><tr><th>Source</th><th>Items</th><th>Note</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderStatus() {
  if (!data) return;
  const failed = data.sources.filter((s) => !s.ok).length;
  const liveTxt = { idle: "", loading: " · checking live HN…", ok: ` · <span class="live">● Live</span> +${live.length}`, error: ' · <span class="warn">live HN unavailable</span>' }[liveState];
  $("#status").innerHTML = `Updated ${esc(ago(data.generated))}${liveTxt}${failed ? ` · <span class="warn">${failed} source(s) failed</span>` : ""}`;
  $("#refresh").classList.toggle("spin", liveState === "loading");
}

function render() {
  renderStatus();
  if (!data) return;
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-current", b.dataset.tab === tab ? "page" : "false"));
  const items = allItems().filter(matches);
  const views = { hot: renderHot, today: renderToday, topics: renderTopics, releases: renderReleases, learn: renderLearn, saved: renderSaved, more: renderMore };
  view.innerHTML = (views[tab] || renderHot)(items);
}

// ---------------------------------------------------------------- events
document.querySelector(".tabs").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-tab]"); if (!b) return;
  tab = b.dataset.tab; history.replaceState(null, "", "#" + tab); render(); window.scrollTo(0, 0);
});
let searchTimer;
$("#search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { query = e.target.value.trim().toLowerCase(); render(); }, 150);
});
$("#refresh").addEventListener("click", async () => {
  // With the backend server this starts a full refresh of every source; on GitHub Pages
  // there is no API (404/405) and the button just reloads data + live Hacker News.
  try {
    const res = await fetch("api/refresh", { method: "POST" });
    if (res.status === 202) setTimeout(() => loadData().then(loadLive), 25000);
  } catch { /* static hosting or offline */ }
  loadData(true).then(loadLive);
});

view.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act],[data-tag],[data-topic],[data-mute],[data-range],[data-setting],[data-learn],[data-progress],[data-hotall]");
  if (!el) return;
  if (el.dataset.hotall) { hotAll = !hotAll; render(); return; }
  if (el.dataset.learn) { learnFilter = el.dataset.learn; render(); return; }
  if (el.dataset.progress) {
    const id = el.dataset.progress, cur = prefs.progress[id] || "todo";
    prefs.progress[id] = PROGRESS[(PROGRESS.indexOf(cur) + 1) % PROGRESS.length];
    savePrefs(); render(); return;
  }
  const cardEl = el.closest(".card");
  const key = cardEl && cardEl.dataset.key;
  const item = key && (allItems().find((i) => i.key === key) || prefs.saved[key]);
  if (el.dataset.act === "open" && key) { prefs.read.add(key); savePrefs(); setTimeout(render, 300); return; }
  e.preventDefault();
  if (el.dataset.act === "more") { const s = cardEl.querySelector(".sum"); s.classList.toggle("clamp"); el.textContent = s.classList.contains("clamp") ? "Show more" : "Show less"; return; }
  if (el.dataset.act === "save" && item) { prefs.saved[key] ? delete prefs.saved[key] : (prefs.saved[key] = item); }
  if (el.dataset.act === "read" && key) { prefs.read.has(key) ? prefs.read.delete(key) : prefs.read.add(key); }
  if (el.dataset.tag) { tab = "topics"; topicFilter = el.dataset.tag; history.replaceState(null, "", "#topics"); }
  if (el.dataset.topic) { topicFilter = topicFilter === el.dataset.topic ? null : el.dataset.topic; }
  if (el.dataset.mute) { const t = el.dataset.mute; prefs.muted.has(t) ? prefs.muted.delete(t) : prefs.muted.add(t); }
  if (el.dataset.range) { todayRange = el.dataset.range; }
  if (el.dataset.setting === "unmute") prefs.muted.clear();
  if (el.dataset.setting === "clear-read" && confirm("Clear read history?")) prefs.read.clear();
  if (el.dataset.setting === "export") {
    const blob = new Blob([JSON.stringify({ read: [...prefs.read], saved: prefs.saved, muted: [...prefs.muted], progress: prefs.progress })], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "radar-prefs.json" }); a.click();
  }
  savePrefs(); render();
});
view.addEventListener("change", async (e) => {
  if (e.target.dataset.setting !== "import" || !e.target.files[0]) return;
  try {
    const d = JSON.parse(await e.target.files[0].text());
    (d.read || []).forEach((k) => prefs.read.add(k)); Object.assign(prefs.saved, d.saved || {}); (d.muted || []).forEach((t) => prefs.muted.add(t));
    Object.assign(prefs.progress, d.progress || {});
    savePrefs(); render();
  } catch { alert("That file is not a Radar export."); }
});

// refresh whenever the app comes back to the foreground (e.g. reopened from home screen)
document.addEventListener("visibilitychange", () => {
  // iOS home-screen apps often skip "pagehide", so also remember the visit when hidden
  if (document.visibilityState === "hidden") store.set("lastVisit", new Date().toISOString());
  if (document.visibilityState === "visible" && data && Date.now() - new Date(data.generated).getTime() > 5 * 60000) loadData().then(loadLive);
});
window.addEventListener("pagehide", () => store.set("lastVisit", new Date().toISOString()));
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});

// ---------------------------------------------------------------- start
render();                       // 1. instant: last data on this device
loadData().then(loadLive);      // 2. fresh data.json, 3. live Hacker News
setInterval(renderStatus, 60000);
