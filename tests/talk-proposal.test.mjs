import assert from "node:assert/strict";
import test from "node:test";
import { changeLine, proposalView } from "../src/talk/proposal.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();

/** Look up interface text in one language, as the interface does. */
function lookup(language) {
  return (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));
}

test("reads a meal move with its times before and after, and whether the set plan changes around it", () => {
  const view = proposalView({ actionType: "change_meal", payload: { date: "2026-10-04", meal: "lunch", title: "Lunch",
    start: "12:30", minutes: 60, scope: "standing", before: { start: "12:00", minutes: 60 }, planChanges: true } }, []);
  assert.deepEqual(view, { kind: "meal", date: "2026-10-04", title: "Lunch", scope: "standing", from: "12:00–13:00",
    to: "12:30–13:30", planChanges: true });
});

test("reads a change to a past task as each field it changes, before and after", () => {
  const view = proposalView({ actionType: "edit_item", payload: { date: "2026-10-01", itemId: "item_1", title: "Review",
    changes: { durationMinutes: 45, status: "partial" }, before: { durationMinutes: 60, status: "done" } } }, []);
  assert.deepEqual(view, { kind: "edit", date: "2026-10-01", title: "Review", changes: [
    { field: "durationMinutes", from: 60, to: 45 }, { field: "status", from: "done", to: "partial" }] });
});

test("reads a past task's removal with its start, its length and whether its day's plan keeps its entry", () => {
  const removal = (inSetPlan) => proposalView({ actionType: "remove_item", payload: { date: "2026-10-01", itemId: "item_1",
    title: "Review", startTime: null, durationMinutes: 30, inSetPlan } }, []);
  assert.deepEqual(removal(false), { kind: "remove", date: "2026-10-01", title: "Review", start: null, minutes: 30, keptByPlan: false });
  assert.equal(removal(true).keptByPlan, true);
  assert.deepEqual([text.en.proposalRemoveKeptEntry, text.zh.proposalRemoveKeptEntry],
    ["The plan set for that day keeps its entry, as history.", "那一天设定的计划保留它的条目，作为历史记录。"]);
});

test("words each change to a past task in both languages", () => {
  const goals = [{ id: "goal_1", title: "Launch" }];
  const en = lookup("en");
  const zh = lookup("zh");
  assert.equal(changeLine({ field: "startTime", from: null, to: "10:00" }, en, "en", goals), "Start: No start time → 10:00");
  assert.equal(changeLine({ field: "status", from: "done", to: "partial" }, en, "en", goals), "Status: Done → Partial");
  assert.equal(changeLine({ field: "goalId", from: "goal_1", to: null }, en, "en", goals), "Goal: Launch → No goal");
  assert.equal(changeLine({ field: "title", from: "Review", to: "Read" }, en, "en", goals), "Title: “Review” → “Read”");
  assert.equal(changeLine({ field: "detail", from: "", to: "Slides" }, en, "en", goals), "Detail: None → “Slides”");
  assert.equal(changeLine({ field: "date", from: "2026-10-01", to: "2026-10-02" }, en, "en", goals), "Date: Thursday 1 October → Friday 2 October");
  assert.equal(changeLine({ field: "durationMinutes", from: 60, to: 45 }, zh, "zh", goals), "时长：1 小时 → 45 分钟");
});

const items = [{ id: "item_1", title: "Statistics, chapter 4", duration_minutes: 60 }];

test("reads a plan proposal as setting a plan when none is set", () => {
  assert.deepEqual(proposalView({ actionType: "select_variant", payload: { date: "2026-09-23", variantId: "v2", variantName: "Focused", reviewedFromVariantName: null } }, items),
    { kind: "set", date: "2026-09-23", to: "Focused" });
});

test("reads a plan proposal as a replacement when a plan is already set", () => {
  assert.deepEqual(proposalView({ actionType: "select_variant", payload: { date: "2026-09-23", variantId: "v2", variantName: "Focused", reviewedFromVariantName: "Balanced" } }, items),
    { kind: "replace", date: "2026-09-23", from: "Balanced", to: "Focused" });
});

test("names the task a shortening changes, and its length before and after", () => {
  assert.deepEqual(proposalView({ actionType: "shorten_future_item", payload: { date: "2026-09-24", itemId: "item_1", durationMinutes: 45 } }, items),
    { kind: "shorten", date: "2026-09-24", title: "Statistics, chapter 4", from: 60, to: 45 });
});

test("still reads a shortening whose task isn't on the day on show", () => {
  assert.deepEqual(proposalView({ actionType: "shorten_future_item", payload: { date: "2026-09-24", itemId: "gone", durationMinutes: 45 } }, items),
    { kind: "shorten", date: "2026-09-24", title: null, from: null, to: 45 });
});

test("names the task a move changes, and its start before and after", () => {
  const timed = [{ ...items[0], start_time: "09:00" }];
  assert.deepEqual(proposalView({ actionType: "move_item", payload: { date: "2026-09-24", itemId: "item_1", startTime: "11:00" } }, timed),
    { kind: "move", date: "2026-09-24", title: "Statistics, chapter 4", from: "09:00", to: "11:00" });
  assert.deepEqual(proposalView({ actionType: "move_item", payload: { date: "2026-09-24", itemId: "gone", startTime: "11:00" } }, timed),
    { kind: "move", date: "2026-09-24", title: null, from: null, to: "11:00" });
});

test("names the task a length change applies to, and its length before and after", () => {
  assert.deepEqual(proposalView({ actionType: "set_length", payload: { date: "2026-09-24", itemId: "item_1", durationMinutes: 10 } }, items),
    { kind: "length", date: "2026-09-24", title: "Statistics, chapter 4", from: 60, to: 10 });
});

test("keeps an unknown proposal's date without guessing what it does", () => {
  assert.deepEqual(proposalView({ actionType: "something_new", payload: { date: "2026-09-25" } }, items), { kind: "other", date: "2026-09-25" });
});
