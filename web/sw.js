// Offline support: app shell from cache, data.json network-first (falls back to last copy).
const CACHE = "radar-v1";
const SHELL = ["./", "index.html", "app.css", "app.js", "manifest.webmanifest", "icon.svg", "icon-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
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
      const copy = res.clone(); caches.open(CACHE).then((c) => c.put("data.json", copy)); return res;
    }).catch(() => caches.match("data.json")));
    return;
  }
  // shell: network first so updates show up, cache when offline
  e.respondWith(fetch(e.request).then((res) => {
    const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return res;
  }).catch(() => caches.match(e.request).then((r) => r || caches.match("index.html"))));
});
