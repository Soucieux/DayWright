import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { countedEntries, dayState, historyMark } from "../src/calendar/dayState.js";
import { interfaceText } from "./interfaceText.mjs";
import { daysBetween, monthDates, shiftMonth } from "../src/calendar/month.js";

test("lays a month out in six Monday-first weeks", () => {
  const dates = monthDates("2026-09");

  assert.equal(dates.length, 42);
  assert.equal(dates[0], "2026-08-31");
  assert.equal(dates[1], "2026-09-01");
  assert.equal(dates[41], "2026-10-11");
});

test("starts on the 1st when a month begins on a Monday", () => {
  assert.equal(monthDates("2026-06")[0], "2026-06-01");
});

test("steps months across a year boundary", () => {
  assert.equal(shiftMonth("2026-12", 1), "2027-01");
  assert.equal(shiftMonth("2026-01", -1), "2025-12");
});

test("counts days between dates in either direction", () => {
  assert.equal(daysBetween("2026-09-23", "2026-09-25"), 2);
  assert.equal(daysBetween("2026-09-23", "2026-09-17"), -6);
  assert.equal(daysBetween("2026-10-24", "2026-10-26"), 2);
});

test("leaves a date without a record empty, never estimated", () => {
  assert.deepEqual(dayState(undefined, "2026-09-07", "2026-09-23"), {
    past: true, empty: true, set: false, recorded: false, done: 0, total: 0, presets: 0, suggested: 0,
  });
});

test("shows a set plan with how much of it was reported done", () => {
  const record = { confirmed: true, entryCount: 9, doneCount: 7, managedCount: 3, planSource: "orchestrator-records-v1" };

  const state = dayState(record, "2026-09-08", "2026-09-23");

  assert.equal(state.set, true);
  assert.equal(state.recorded, false);
  assert.deepEqual([state.done, state.total], [7, 9]);
});

test("marks a recorded day without a set plan as recorded", () => {
  const state = dayState({ confirmed: false, entryCount: 2, doneCount: 1, managedCount: 2, planSource: null }, "2026-09-11", "2026-09-23");

  assert.equal(state.recorded, true);
  assert.deepEqual([state.done, state.total], [0, 0]);
});

test("counts presets and waiting suggestions only ahead of today", () => {
  const record = { confirmed: false, entryCount: 2, doneCount: 0, managedCount: 2, suggestedCount: 1, planSource: null };

  const ahead = dayState(record, "2026-09-25", "2026-09-23");

  assert.deepEqual([ahead.presets, ahead.suggested, ahead.recorded, ahead.past], [2, 1, false, false]);
  assert.equal(dayState(record, "2026-09-23", "2026-09-23").presets, 0);
});

test("a day's counts leave out a past plan's entry for a removed task, which stays on show", () => {
  const entries = [{ title: "Piano", completion_status: "done", removed: false },
    { title: "Morning chess", completion_status: "done", removed: true }];

  assert.deepEqual(countedEntries(entries).map((entry) => entry.title), ["Piano"]);
  assert.equal(entries.length, 2);
});

test("a past plan's entry for a task that left its day is marked Removed, or Moved to its new day", () => {
  const text = interfaceText();
  const lookup = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match);
  const moved = { removed: true, moved_to: "2026-10-04" };
  assert.deepEqual([historyMark(moved, lookup("en"), "en"), historyMark(moved, lookup("zh"), "zh"),
    historyMark({ removed: true, moved_to: null }, lookup("en"), "en"), historyMark({ removed: true }, lookup("zh"), "zh"),
    historyMark({ removed: false }, lookup("en"), "en")],
  ["Moved to Sun 4 Oct", "已移到10月4日周日", "Removed", "已移除", null]);
});

test("the legend's descriptions start at the edge, as Patterns' sentences do, rather than spreading out at phone width", () => {
  const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
  assert.match(css, /\.dw-legend-text \{[^}]*text-align: start; hyphens: manual;/);
});
