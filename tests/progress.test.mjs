import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { FINISHING_MIN_DAYS, FOLLOW_PARTS, areaDayBars, finishingBars, finishingTotals, followThroughParts,
  followThroughTotals, goalBurnup, padDays, planFollowThrough } from "../src/ui/progress.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const AREAS = ["learning", "life", "work", "project"];

test("a period's days are all listed, a day the service didn't list counting nothing", () => {
  assert.deepEqual(padDays("2026-10-05", "2026-10-07", [{ date: "2026-10-06", scheduled: 2, done: 1, minutes: { work: 30 } }]), [
    { date: "2026-10-05", scheduled: 0, done: 0, minutes: {} },
    { date: "2026-10-06", scheduled: 2, done: 1, minutes: { work: 30 } },
    { date: "2026-10-07", scheduled: 0, done: 0, minutes: {} },
  ]);
});

test("done by area stacks each day's fully done time by area, against the fullest day", () => {
  const bars = areaDayBars([{ date: "2026-10-05", minutes: { work: 60, learning: 30 } }, { date: "2026-10-06", minutes: {} },
    { date: "2026-10-07", minutes: { life: 45 } }], AREAS);
  assert.deepEqual(bars.map(({ total, height, empty }) => ({ total, height, empty })),
    [{ total: 90, height: 100, empty: false }, { total: 0, height: 0, empty: true }, { total: 45, height: 50, empty: false }]);
  assert.deepEqual(bars[0].parts, [{ domain: "learning", minutes: 30, height: 33.3 }, { domain: "work", minutes: 60, height: 66.7 }],
    "in the areas' own order, each as a share of the fullest day");
  assert.deepEqual(bars[1].parts, []);
});

test("finishing is each day's share of tasks fully done, and shows from enough days with tasks", () => {
  const days = [{ date: "2026-10-05", scheduled: 3, done: 2 }, { date: "2026-10-06", scheduled: 0, done: 0 },
    { date: "2026-10-07", scheduled: 4, done: 4 }];
  assert.deepEqual(finishingBars(days).map(({ rate, height, empty }) => ({ rate, height, empty })),
    [{ rate: 67, height: 67, empty: false }, { rate: null, height: 0, empty: true }, { rate: 100, height: 100, empty: false }]);
  assert.deepEqual(finishingTotals(days), { days: 2, done: 6, scheduled: 7, rate: 86, enough: true });
  assert.equal(FINISHING_MIN_DAYS, 2);
  assert.equal(finishingTotals(days.slice(0, 2)).enough, false, "one day with tasks is too little");
});

test("follow-through stacks a set plan's entries from done to not reported, leaving out parts with none", () => {
  assert.deepEqual(FOLLOW_PARTS, ["done", "partial", "moved", "skipped", "unreported"]);
  assert.deepEqual(followThroughParts({ done: 4, partial: 1, moved: 1, skipped: 1, unreported: 2 }), {
    total: 9, parts: [{ key: "done", count: 4, share: 44.4 }, { key: "partial", count: 1, share: 11.1 },
      { key: "moved", count: 1, share: 11.1 }, { key: "skipped", count: 1, share: 11.1 }, { key: "unreported", count: 2, share: 22.2 }] });
  assert.deepEqual(followThroughParts({ done: 2, partial: 0, moved: 0, skipped: 0, unreported: 0 }).parts, [{ key: "done", count: 2, share: 100 }]);
  assert.deepEqual(followThroughTotals([{ date: "a", done: 1, partial: 1, moved: 1, skipped: 1, unreported: 0 },
    { date: "b", done: 2, partial: 0, moved: 0, skipped: 0, unreported: 1 }]),
  { days: 2, done: 3, partial: 1, moved: 1, skipped: 1, unreported: 1 });
});

test("a day's set plan is followed as its entries were reported, moved entries in, removed ones out", () => {
  const entries = [{ completion_status: "done" }, { completion_status: "planned" }, { completion_status: "skipped" },
    { completion_status: "partial" }, { completion_status: "done", removed: true, moved_to: "2026-10-09" },
    { completion_status: "done", removed: true, moved_to: null },
    { completion_status: "planned", source: { goalStatus: "paused" } }, { completion_status: "done", source: { goalStatus: "paused" } }];
  assert.deepEqual(planFollowThrough(entries), { done: 2, partial: 1, moved: 1, skipped: 1, unreported: 1 },
    "an entry still to do whose goal is paused is left out, as Summary leaves it out; one reported stays");
});

test("a goal's burn-up: a column a week of its steps done so far, the weeks ahead outlined to what is planned", () => {
  const items = [{ date: "2026-09-22", status: "done" }, { date: "2026-09-30", status: "done" }, { date: "2026-10-01", status: "skipped" },
    { date: "2026-10-02", status: "planned" }, { date: "2026-10-06", status: "done" }, { date: "2026-10-09", status: "planned" },
    { date: "2026-10-20", status: "planned" }];
  const burnup = goalBurnup(items, "2026-09-23T10:00:00Z", "2026-10-07");
  assert.deepEqual(burnup.weeks, [
    { start: "2026-09-21", done: 1, planned: 1, current: false, future: false },
    { start: "2026-09-28", done: 2, planned: 2, current: false, future: false },
    { start: "2026-10-05", done: 3, planned: 4, current: true, future: false },
    { start: "2026-10-12", done: null, planned: 4, current: false, future: true },
    { start: "2026-10-19", done: null, planned: 5, current: false, future: true },
  ]);
  assert.deepEqual([burnup.total, burnup.done, burnup.ahead, burnup.through], [7, 3, 2, "2026-10-20"],
    "every step counts toward the total; a past step never reported is neither done nor ahead");
  assert.deepEqual(goalBurnup([], "2026-09-23T10:00:00Z", "2026-10-07"), { weeks: [], total: 0, done: 0, ahead: 0, through: null });
});

test("Summary's reports show the graphs their period has, Today the finishing week, Calendar the day's follow-through", () => {
  const reports = source("calendar/SummaryReports.jsx");
  assert.match(reports, /report\.graphs && <ReportGraphs kind=\{report\.periodKind\} graphs=\{report\.graphs\} \/>/);
  const graphs = reports.slice(reports.indexOf("function ReportGraphs("), reports.indexOf("\n}\n", reports.indexOf("function ReportGraphs(")));
  assert.match(graphs, /kind === "day"/);
  assert.match(graphs, /<DoneByArea /);
  assert.match(graphs, /<FinishingBars /);
  assert.match(graphs, /<FollowThroughDays /);
  assert.match(source("today/TodayScreen.jsx"), /<FinishingCard days=\{day\.finishingWeek\}/);
  assert.match(source("calendar/DayPanel.jsx"), /<FollowThroughBar counts=\{planFollowThrough\(planEntries\)\}/);
  assert.match(source("records/GoalsScreen.jsx"), /<GoalBurnup goal=\{goal\} today=\{today\} \/>/);
});

test("every graph says its numbers in words and has its own empty line", () => {
  const graphs = source("ui/ProgressGraphs.jsx");
  for (const key of ["doneByAreaEmpty", "finishingTooFew", "followEmpty", "goalProgressEmpty"]) {
    assert.match(graphs, new RegExp(`t\\("${key}"`), key);
  }
  for (const key of ["doneByAreaDay", "doneByAreaNone", "finishingDay", "finishingDayNone", "followBarLabel", "goalProgressWeek",
    "goalProgressAhead", "goalProgressCurrent"]) {
    assert.match(graphs, new RegExp(`aria-label=\\{t\\("${key}"|t\\("${key}"`), `${key} names a bar`);
  }
});

test("the graphs' text reads in English and Chinese", () => {
  const keys = ["reportDoneByArea", "reportFinishing", "reportFollowThrough", "doneByAreaLabel", "doneByAreaDay", "doneByAreaNone",
    "doneByAreaTotal", "doneByAreaEmpty", "finishingLabel", "finishingDay", "finishingDayNone", "finishingTotal", "finishingTooFew",
    "followLabel", "followMoved", "followBarLabel", "followTotal", "followEmpty", "followNoPlanDay", "finishingCardTitle",
    "finishingCardCaption", "finishingToday", "goalProgressHeading", "goalProgressLabel", "goalProgressWeek", "goalProgressAhead",
    "goalProgressCurrent",
    "goalProgressLine", "goalProgressAheadLine", "goalProgressEmpty", "goalProgressKey"];
  for (const key of keys) {
    assert.ok(text.en[key], `${key} in English`);
    assert.ok(text.zh[key], `${key} in Chinese`);
  }
});
