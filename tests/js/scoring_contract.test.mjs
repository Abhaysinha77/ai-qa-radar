// Contract test (JS side): app.js must score and tag exactly like the Python collector.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const src = fs.readFileSync(path.join(root, "web/app.js"), "utf8");
const fixture = JSON.parse(fs.readFileSync(path.join(root, "tests/fixtures/scoring_cases.json"), "utf8"));

// Load only the pure scoring functions from app.js (no DOM needed).
const start = src.indexOf("const rx =");
const rxLine = src.slice(start, src.indexOf("\n", start));
const fns = src.slice(src.indexOf("function tagsFor"), src.indexOf("// ---------------------------------------------------------------- data"));
const ctx = { data: { ranking: fixture.ranking, tags: fixture.tags, tag_exclude: fixture.tag_exclude }, Date, Math, RegExp, Object, String };
vm.createContext(ctx);
vm.runInContext(`${rxLine}\n${fns}\nthis.scoreItem = scoreItem; this.tagsFor = tagsFor;`, ctx);

for (const c of fixture.cases) {
  test(`JS matches Python: "${c.item.title || "(empty title)"}"`, () => {
    const got = ctx.scoreItem({ ...c.item, summary: "" });
    assert.equal(got.quadrant, c.expected.quadrant);
    assert.equal(got.importance, c.expected.importance);
    assert.equal(got.urgency, c.expected.urgency);
    assert.equal(JSON.stringify(ctx.tagsFor({ title: c.item.title })), JSON.stringify(c.tags));
  });
}
