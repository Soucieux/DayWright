import assert from "node:assert/strict";
import test from "node:test";
import { cardDay, changeLine, leftOutLine, proposalView } from "../src/talk/proposal.js";
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
    to: "12:30–13:30", planChanges: true, replaces: [] });
});

test("reads a meal ending at midnight as 24:00, and the one-day times a standing move replaces", () => {
  const view = proposalView({ actionType: "change_meal", payload: { date: "2026-10-04", meal: "dinner", title: "Dinner",
    start: "23:00", minutes: 60, scope: "standing", before: { start: "18:00", minutes: 60 }, planChanges: false,
    replaces: [{ date: "2026-10-09", start: "19:00", minutes: 45 }] } }, []);
  assert.equal(view.to, "23:00–24:00");
  assert.deepEqual(view.replaces, [{ date: "2026-10-09", range: "19:00–19:45" }]);
  assert.deepEqual([lookup("en")("proposalMealReplaces", { meal: "dinner", days: "Friday 9 October (19:00–19:45)" }),
    lookup("zh")("proposalMealReplaces", { meal: "晚餐", days: "10月9日星期五（19:00–19:45）" })],
  ["It replaces the one-day dinner time on Friday 9 October (19:00–19:45).",
    "它将取代10月9日星期五（19:00–19:45）的单日晚餐时间。"]);
});

test("names a card's day: today and tomorrow without “on”, any other day by its date with it", () => {
  for (const [language, expected] of [["en", ["today", "tomorrow", "on Fri 9 Oct"]], ["zh", ["今天", "明天", "10月9日周五"]]]) {
    assert.deepEqual(["2026-10-04", "2026-10-05", "2026-10-09"]
      .map((day) => cardDay(day, "2026-10-04", lookup(language), language).on), expected, language);
  }
  assert.equal(cardDay("2026-10-09", "2026-10-04", lookup("en"), "en").plain, "Fri 9 Oct");
  const en = lookup("en");
  const zh = lookup("zh");
  assert.deepEqual([en("proposalMealDayTitle", { meal: "dinner", when: "today" }), en("proposalMoveTitle", { when: "tomorrow" }),
    en("proposalMealDayTitle", { meal: "dinner", when: "on Fri 9 Oct" }), en("proposalRemoveTitle", { when: "on Fri 9 Oct" }),
    zh("proposalMealDayTitle", { meal: "晚餐", when: "今天" }), zh("proposalMoveTitle", { when: "10月9日周五" })],
  ["Move dinner today", "Move 1 task tomorrow", "Move dinner on Fri 9 Oct", "Remove 1 task on Fri 9 Oct",
    "调整今天的晚餐时间", "移动10月9日周五的 1 个任务"]);
});

test("reads a repeat started, stopped or switched from a past day, from its first changed day", () => {
  const view = proposalView({ actionType: "repeat_item", payload: { date: "2026-09-28", itemId: "item_1", title: "Read",
    mode: "start", repeatKind: "daily", seriesId: null, startsOn: "2026-10-09" } }, []);
  assert.deepEqual(view, { kind: "repeat", date: "2026-09-28", title: "Read", mode: "start", repeatKind: "daily",
    startsOn: "2026-10-09", removes: [] });
  assert.deepEqual(proposalView({ actionType: "repeat_item", payload: { date: "2026-09-28", itemId: "item_1", title: "Read",
    mode: "stop", repeatKind: "none", seriesId: "item_1", startsOn: "2026-10-04", removes: ["2026-10-04", "2026-10-05"] } }, []).removes,
  ["2026-10-04", "2026-10-05"]);
  assert.deepEqual([lookup("en")("proposalRepeatRemoves", { days: "today, tomorrow" }),
    lookup("zh")("proposalRepeatRemoves", { days: "今天、明天" })],
  ["Its days still to do are removed: today, tomorrow.", "以下尚未完成的那几天将被删除：今天、明天。"]);
  const en = lookup("en");
  const zh = lookup("zh");
  assert.deepEqual([en("proposalRepeatFrom", { kind: en("repeatDaily"), day: "Fri 9 Oct" }),
    en("proposalRepeatStops", { day: "tomorrow" }), zh("proposalRepeatFrom", { kind: zh("repeatWeekly"), day: "10月9日周五" })],
  ["Repeats daily from Fri 9 Oct; earlier days stay as they were.", "Stops repeating from tomorrow; earlier days stay as they were.",
    "从10月9日周五起每周重复；之前的日子保持不变。"]);
});

test("reads what a past task's change left out, and says why", () => {
  const view = proposalView({ actionType: "edit_item", payload: { date: "2026-10-03", itemId: "item_1", title: "Review",
    changes: { status: "partial" }, before: { status: "done" }, leftOut: ["durationMinutes"] } }, []);
  assert.deepEqual(view.leftOut, ["durationMinutes"]);
  assert.deepEqual([leftOutLine(view.leftOut, lookup("en"), "en"), leftOutLine(["startTime", "durationMinutes"], lookup("zh"), "zh")],
    ["Left out: length. On its past day a task keeps its place.", "未包含：开始、时长。任务在过去的日子里保持原位。"]);
});

test("reads the days a repeating task's change reaches, and says how many", () => {
  const view = proposalView({ actionType: "edit_item", payload: { date: "2026-10-03", itemId: "item_1", title: "Stretch",
    changes: { title: "Morning stretch" }, before: { title: "Stretch" }, days: ["2026-10-03", "2026-10-04"] } }, []);
  assert.deepEqual(view.days, ["2026-10-03", "2026-10-04"]);
  assert.deepEqual([lookup("en")("proposalDaysChange", { count: 2, days: "Sat 3 Oct, Sun 4 Oct" }),
    lookup("en")("proposalDayChanges", { day: "Sat 3 Oct" }), lookup("zh")("proposalDaysChange", { count: 2, days: "10月3日周六、10月4日周日" })],
  ["2 days change: Sat 3 Oct, Sun 4 Oct.", "Only Sat 3 Oct changes.", "将修改 2 天：10月3日周六、10月4日周日。"]);
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
