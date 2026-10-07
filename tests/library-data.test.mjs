import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import test from "node:test";
import * as libraryData from "../src/library/libraryData.js";
import { addedLabel, goalSources, importHeaders, libraryName, linkChoices, matchView, sourceView, studyLibrary, tasksByGoal }
  from "../src/library/libraryData.js";
import { CARD_TEXT } from "../src/records/areaOverview.js";
import { interfaceText } from "./interfaceText.mjs";

/** An ISO timestamp for a local date and time, so the checks hold in any time zone. */
const at = (year, month, day, hour, minute) => new Date(year, month - 1, day, hour, minute).toISOString();
const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const task = (itemId, goalId, goalTitle, role = "reference") => ({ itemId, title: itemId, date: "2026-10-07", goalId, goalTitle, role });
const ITEMS = [
  { id: "a", title: "Grammar", sourceType: "note", tasks: [task("Lesson 4", "spanish", "Spanish")] },
  { id: "b", title: "Study tips", sourceType: "note", tasks: [] },
  { id: "c", title: "Desk plan.md · 0123456789ab", sourceType: "document", tasks: [task("Review", null, null, "checklist")] },
];

test("names imported files without their revision and reads their kind", () => {
  assert.deepEqual(sourceView({ title: "Stats course plan.md · 3f2a9c1b0d4e", sourceType: "document" }),
    { name: "Stats course plan.md", kind: "markdown", group: "files" });
  assert.equal(sourceView({ title: "Syllabus.PDF · 0123456789ab", sourceType: "document" }).kind, "pdf");
  assert.equal(sourceView({ title: "Budget 2026.docx · abcdefabcdef", sourceType: "document" }).kind, "word");
  assert.equal(libraryName("Lesson 4.md · 0123456789ab"), "Lesson 4.md");
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

test("a source links no goal: a goal holds the sources its tasks use", () => {
  assert.deepEqual(goalSources(ITEMS, "spanish").map((item) => item.id), ["a"]);
  assert.deepEqual(goalSources(ITEMS, "piano"), []);
  for (const name of ["goalLinks", "studyGoals", "areaLinks", "libraryOf"]) assert.equal(name in libraryData, false, name);
});

test("a source's tasks are grouped under their goals, those without one last", () => {
  const grouped = tasksByGoal([task("Lesson 4", "spanish", "Spanish"), task("Practice", "spanish", "Spanish"),
    task("Review", null, null, "checklist")]);
  assert.deepEqual(grouped.map((group) => [group.goalTitle, group.tasks.map((entry) => entry.itemId)]),
    [["Spanish", ["Lesson 4", "Practice"]], [null, ["Review"]]]);
});

test("a Learn task offers to link each Library item it doesn't use yet, by name", () => {
  assert.deepEqual(linkChoices(ITEMS, ["a"]).map((item) => item.id), ["c", "b"]);
});

test("a file is imported by its name alone, never with an area or a goal", () => {
  const headers = importHeaders("Lesson 4.md");
  assert.equal(atob(headers["X-DayWright-Filename"]), "Lesson 4.md");
  assert.deepEqual(Object.keys(headers).sort(), ["Content-Type", "X-DayWright-Filename"]);
});

test("a search result names its source and which part it is", () => {
  assert.deepEqual(matchView({ sourceTitle: "Lesson 4.md · 0123456789ab", sourceType: "document", content: "Verb endings.",
    chunkIndex: 1 }), { name: "Lesson 4.md", passage: "Verb endings.", part: 2 });
});

test("Learn's Library card lists the sources tasks use first, then the rest, newest first", () => {
  const items = [{ id: "new", tasks: [] }, { id: "used", tasks: [task("Lesson 4", null, null)] }, { id: "old", tasks: [] }];
  assert.deepEqual(studyLibrary(items).map((item) => item.id), ["used", "new", "old"]);
});

test("no area or goal anywhere on the Library screen or its sheets, and no Edit for one", () => {
  for (const name of readdirSync(new URL("../src/library", import.meta.url)).filter((file) => /\.jsx?$/.test(file))) {
    assert.doesNotMatch(source(`library/${name}`), /AreaTag|DOMAINS|fieldArea|fieldGoal|areas\/suggest|X-DayWright-(Area|Goal)|\bdomain\b|LibraryLinksSheet/, name);
  }
  assert.equal(text.en.libraryLinksTitle, undefined);
});

test("only Learn has a Library card, and only a Learning goal's sheet lists the sources its tasks use, with no Add", () => {
  const screen = source("records/AreaScreen.jsx");
  assert.match(screen, /domain === "learning" && <LibraryCard /);
  assert.equal((screen.match(/<LibraryCard /g) || []).length, 1);
  assert.match(source("records/AreaCards.jsx"), /studyLibrary\(items\)/);
  const goals = source("records/GoalsScreen.jsx");
  assert.match(goals, /goal\?\.domain === "learning" && \(\s*<section className="dw-goal-sheet-library"/);
  assert.match(goals, /goalSources\(library, goal\.id\)/);
  assert.doesNotMatch(goals, /addToLibraryFromGoal|onAddToLibrary/);
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

test("the goal sheet and Learn's page each have a Library section, and the Library says it stays on this Mac but for a learning task's lookups", () => {
  assert.deepEqual([text.en.librarySection, text.zh.librarySection], ["Library", "资料库"]);
  assert.match(source("records/GoalsScreen.jsx"), /t\("librarySection"\)/);
  assert.equal(CARD_TEXT.library.title, "librarySection");
  assert.match(source("records/AreaCards.jsx"), /CARD_TEXT\.library\.title/);
  assert.equal(text.en.searchLibraryLabel, "Search your library");
  assert.equal(text.en.libraryOfflineLine,
    "Everything stays on this Mac; DayWright only looks a website up when you create a learning task from it, and again when that task starts.");
  assert.ok(text.zh.libraryOfflineLine);
});

test("the old online lookup and network log stay gone: a learning task's website lookups are the only ones", () => {
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
