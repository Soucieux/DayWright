import assert from "node:assert/strict";
import test from "node:test";
import { addedLabel, entriesOn, sourceView } from "../src/library/libraryData.js";

/** An ISO timestamp for a local date and time, so the checks hold in any time zone. */
const at = (year, month, day, hour, minute) => new Date(year, month - 1, day, hour, minute).toISOString();

test("names imported files without their revision and reads their kind", () => {
  assert.deepEqual(sourceView({ title: "Stats course plan.md · 3f2a9c1b0d4e", sourceType: "document" }),
    { name: "Stats course plan.md", kind: "markdown", group: "files", fromWeb: false });
  assert.equal(sourceView({ title: "Syllabus.PDF · 0123456789ab", sourceType: "document" }).kind, "pdf");
  assert.equal(sourceView({ title: "Budget 2026.docx · abcdefabcdef", sourceType: "document" }).kind, "word");
});

test("keeps a name whose ending only looks like a revision", () => {
  assert.equal(sourceView({ title: "Notes.md · draft", sourceType: "document" }).name, "Notes.md · draft");
});

test("groups notes and web introductions as notes, marking only the web ones", () => {
  assert.deepEqual(sourceView({ title: "Fridge", sourceType: "note", sourceUrl: "" }),
    { name: "Fridge", kind: "note", group: "notes", fromWeb: false });
  assert.equal(sourceView({ title: "Wikipedia · Kalman filter · By level", sourceType: "import",
    sourceUrl: "https://en.wikipedia.org/wiki/Kalman_filter" }).fromWeb, true);
});

test("says today's additions by time and older ones by day and month", () => {
  assert.equal(addedLabel(at(2026, 9, 23, 14, 2), "2026-09-23", "en", "today"), "today 14:02");
  assert.equal(addedLabel(at(2026, 9, 2, 9, 0), "2026-09-23", "en", "today"), "2 Sept");
  assert.equal(addedLabel(at(2026, 9, 2, 9, 0), "2026-09-23", "zh", "今天"), "9月2日");
});

test("keeps only the log entries made on the given local date", () => {
  const entries = [{ id: "a", happenedAt: at(2026, 9, 23, 0, 5) }, { id: "b", happenedAt: at(2026, 9, 22, 23, 55) }];
  assert.deepEqual(entriesOn(entries, "2026-09-23").map((entry) => entry.id), ["a"]);
});
