import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import test from "node:test";
import { addedLabel, areaLinks, goalLinks, importHeaders, libraryOf, matchView, sourceView } from "../src/library/libraryData.js";
import { CARD_TEXT } from "../src/records/areaOverview.js";
import { interfaceText } from "./interfaceText.mjs";

/** An ISO timestamp for a local date and time, so the checks hold in any time zone. */
const at = (year, month, day, hour, minute) => new Date(year, month - 1, day, hour, minute).toISOString();
const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const ITEMS = [
  { id: "a", title: "Grammar", sourceType: "note", domain: "learning", goalId: "spanish" },
  { id: "b", title: "Study tips", sourceType: "note", domain: "learning", goalId: null },
  { id: "c", title: "Desk plan.md · 0123456789ab", sourceType: "document", domain: "work", goalId: null },
];

test("names imported files without their revision and reads their kind", () => {
  assert.deepEqual(sourceView({ title: "Stats course plan.md · 3f2a9c1b0d4e", sourceType: "document" }),
    { name: "Stats course plan.md", kind: "markdown", group: "files" });
  assert.equal(sourceView({ title: "Syllabus.PDF · 0123456789ab", sourceType: "document" }).kind, "pdf");
  assert.equal(sourceView({ title: "Budget 2026.docx · abcdefabcdef", sourceType: "document" }).kind, "word");
});

test("keeps a name whose ending only looks like a revision, and a note is a note", () => {
  assert.equal(sourceView({ title: "Notes.md · draft", sourceType: "document" }).name, "Notes.md · draft");
  assert.deepEqual(sourceView({ title: "Fridge", sourceType: "note" }), { name: "Fridge", kind: "note", group: "notes" });
});

test("says today's additions by time and older ones by day and month", () => {
  assert.equal(addedLabel(at(2026, 9, 23, 14, 2), "2026-09-23", "en", "today"), "today 14:02");
  assert.equal(addedLabel(at(2026, 9, 2, 9, 0), "2026-09-23", "en", "today"), "2 Sept");
  assert.equal(addedLabel(at(2026, 9, 2, 9, 0), "2026-09-23", "zh", "今天"), "9月2日");
});

test("the area switch keeps every note and file, or one area's", () => {
  assert.deepEqual(libraryOf(ITEMS, { domain: "all" }).map((item) => item.id), ["a", "b", "c"]);
  assert.deepEqual(libraryOf(ITEMS, { domain: "learning" }).map((item) => item.id), ["a", "b"]);
  assert.deepEqual(libraryOf(ITEMS, { domain: "life" }), []);
});

test("a goal's Library lists that goal's notes and files, and an area's lists the area's", () => {
  assert.deepEqual(libraryOf(ITEMS, { goalId: "spanish" }).map((item) => item.id), ["a"]);
  assert.deepEqual(libraryOf(ITEMS, { domain: "work" }).map((item) => item.id), ["c"]);
});

test("adding from a goal or an area starts linked to it", () => {
  assert.deepEqual(goalLinks({ id: "spanish", domain: "learning", title: "Spanish" }), { domain: "learning", goalId: "spanish" });
  assert.deepEqual(areaLinks("project"), { domain: "project", goalId: null });
});

test("a file is imported with its area, and its goal when it has one", () => {
  const linked = importHeaders("Lesson 4.md", { domain: "learning", goalId: "spanish" });
  assert.equal(atob(linked["X-DayWright-Filename"]), "Lesson 4.md");
  assert.deepEqual([linked["X-DayWright-Area"], linked["X-DayWright-Goal"]], ["learning", "spanish"]);
  assert.equal("X-DayWright-Goal" in importHeaders("Notes.md", { domain: "life", goalId: null }), false);
});

test("a search result names its note or file, its area and its goal", () => {
  assert.deepEqual(matchView({ sourceTitle: "Lesson 4.md · 0123456789ab", sourceType: "document", domain: "learning",
    goalTitle: "Spanish", content: "Verb endings.", chunkIndex: 1 }),
  { name: "Lesson 4.md", domain: "learning", goalTitle: "Spanish", passage: "Verb endings.", part: 2 });
});

test("on screen the Library never calls its notes and files sources", () => {
  const library = readdirSync(new URL("../src/library", import.meta.url)).filter((name) => name.endsWith(".jsx"))
    .map((name) => source(`library/${name}`)).join("\n");
  const keys = [...library.matchAll(/\bt\("(\w+)"/g)].map((match) => match[1]);
  assert.ok(keys.length > 10);
  for (const key of keys) {
    assert.ok(text.en[key] && text.zh[key], key);
    assert.doesNotMatch(text.en[key], /\bsources?\b/i, key);
  }
});

test("the goal sheet and the area page each have a Library section, and the Library says it stays offline", () => {
  assert.deepEqual([text.en.librarySection, text.zh.librarySection], ["Library", "资料库"]);
  assert.match(source("records/GoalsScreen.jsx"), /t\("librarySection"\)/);
  assert.equal(CARD_TEXT.library.title, "librarySection");
  assert.match(source("records/AreaCards.jsx"), /CARD_TEXT\.library\.title/);
  assert.equal(text.en.addToLibraryFromGoal, "Add note or file");
  assert.equal(text.en.searchLibraryLabel, "Search your library");
  assert.equal(text.en.libraryOfflineLine, "Everything here stays on this Mac. DayWright doesn't go online.");
  assert.ok(text.zh.libraryOfflineLine);
});

test("no online lookup or network log remains in the interface", () => {
  assert.equal(existsSync(new URL("../src/library/TopicLookup.jsx", import.meta.url)), false);
  assert.equal(existsSync(new URL("../src/library/NetworkLog.jsx", import.meta.url)), false);
  for (const key of ["lookUpTitle", "fetchIntroQuestion", "networkLogTitle", "onlineLookupsToday", "whatStaysTitle", "fromTheWeb"]) {
    assert.equal(text.en[key], undefined, key);
  }
  for (const path of ["App.jsx", "workspace.js", "shell/Shell.jsx", "talk/TalkMessage.jsx"]) {
    assert.doesNotMatch(source(path), /network-log|networkLog|NetworkPill|sourceUrl/, path);
  }
});

test("Ava's replies name the Library, never sources", () => {
  for (const key of [...source("talk/TalkMessage.jsx").matchAll(/\bt\("(\w+)"/g)].map((match) => match[1])) {
    assert.doesNotMatch(text.en[key], /\bsources?\b/i, key);
  }
});
