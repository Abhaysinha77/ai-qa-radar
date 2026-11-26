// Offline support: app shell from cache, data.json network-first (falls back to last copy).
const CACHE = "kairoq-v7";
const SHELL = ["./", "index.html", "app.css?v=7", "app.js?v=7", "manifest.webmanifest", "icon.svg", "icon-192.png"];
const OPTIONAL = ["fonts/geist.woff2", "fonts/geist-mono.woff2"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL).then(() => Promise.allSettled(OPTIONAL.map((f) => c.add(f))))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return; // live HN goes straight to the network
  if (url.pathname.endsWith("data.json")) {
    e.respondWith(fetch(e.request).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put("data.json", copy)); }
      return res;
    }).catch(() => caches.match("data.json")));
    return;
  }
  // shell: network first so updates show up, cache when offline. Only good (200) answers are
  // cached, and only page navigations fall back to index.html (never serve HTML as CSS/JS).
  e.respondWith(fetch(e.request).then((res) => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
    return res;
  }).catch(() => caches.match(e.request, { ignoreSearch: e.request.mode !== "navigate" })
    .then((r) => r || (e.request.mode === "navigate" ? caches.match("index.html") : Response.error()))));
});
