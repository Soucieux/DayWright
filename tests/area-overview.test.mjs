import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { AREA_ADD_CHOICES, AREA_MEANINGS, AREA_SCREEN_TEXT, EMPTY_STATES, askMoveText, barTime, byDay, carryStatusText, dayRange, habitRule,
  habitStopped, noteIcon, projectStatusText, streakText } from "../src/records/areaOverview.js";
import { suggestsArea } from "../src/records/taskDraft.js";
import { noticeText } from "../src/talk/notices.js";
import { interfaceText } from "./interfaceText.mjs";

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);
const text = interfaceText();

test("each area has its one-line meaning in both languages, by the purpose rule", () => {
  assert.deepEqual(Object.keys(AREA_MEANINGS), ["work", "project", "learning", "life"]);
  assert.deepEqual(Object.values(AREA_MEANINGS).map((key) => text.en[key]), [
    "Someone else expects it.", "A step toward something you're building that has an end.",
    "The point is getting better at something.", "Everything else."]);
  assert.deepEqual(Object.values(AREA_MEANINGS).map((key) => text.zh[key]), [
    "有人在等你完成它。", "朝着一件有终点的事迈出的一步。", "目的是让自己在某方面变得更好。", "其他一切。"]);
});

test("the task form asks for an area only for a new task without an area or goal of its own, once it has a title", () => {
  const draft = { title: "Reply to Anna", goalId: "" };
  assert.equal(suggestsArea(null, undefined, draft, false), true);
  assert.equal(suggestsArea(null, {}, { ...draft, title: "  " }, false), false);
  assert.equal(suggestsArea(null, { domain: "work" }, draft, false), false);
  assert.equal(suggestsArea(null, undefined, { ...draft, goalId: "goal_1" }, false), false);
  assert.equal(suggestsArea(null, undefined, draft, true), false);
  assert.equal(suggestsArea({ id: "item_1" }, undefined, draft, false), false);
});

test("a habit's streak is counted in days, or in weeks for a weekly repeat", () => {
  assert.equal(streakText({ kind: "daily", streak: 3 }, t), 'streakDays {"count":3}');
  assert.equal(streakText({ kind: "weekly", streak: 2 }, t), 'streakWeeks {"count":2}');
  assert.equal(streakText({ kind: "daily", streak: 0 }, t), "streakNone");
});

test("a card's time window names its days, a week reading Mon 5 – Sun 11 Oct", () => {
  assert.equal(dayRange("2026-10-05", "2026-10-11", "en"), "Mon 5 – Sun 11 Oct");
  assert.equal(dayRange("2026-09-28", "2026-10-04", "en"), "Mon 28 Sept – Sun 4 Oct");
  assert.equal(dayRange("2026-10-05", "2026-10-11", "zh"), "10月5日周一至11日周日");
  assert.equal(dayRange("2026-09-28", "2026-10-04", "zh"), "9月28日周一至10月4日周日");
});

test("a habit says its rule and since when, and that it stopped this week", () => {
  assert.equal(habitRule({ kind: "daily", since: "2026-10-01" }, t, "en"), 'habitDailySince {"date":"1 Oct"}');
  assert.equal(habitRule({ kind: "weekly", weekday: 0, since: "2026-09-28" }, t, "en"),
    'habitWeeklySince {"weekday":"Mon","date":"28 Sept"}');
  assert.equal(habitRule({ kind: "weekly", weekday: 0, since: "2026-09-28" }, t, "zh"),
    'habitWeeklySince {"weekday":"周一","date":"9月28日"}');
  assert.equal(habitStopped({ stoppedOn: "2026-10-08" }, t, "en"), 'habitStopped {"day":"Thu"}');
  assert.equal(habitStopped({ stoppedOn: null }, t, "en"), null);
});

test("a carry-over says it was not reported, is partly done, or moved on to a day", () => {
  assert.equal(carryStatusText({ date: "2026-10-02", status: "planned" }, t, "en"), "notReportedShort");
  assert.equal(carryStatusText({ date: "2026-10-02", status: "partial" }, t, "en"), "carryPartlyDone");
  assert.equal(carryStatusText({ date: "2026-09-30", movedTo: "2026-10-04" }, t, "en"), 'entryMovedTo {"day":"Sun 4 Oct"}');
});

test("Ask Ava to move words the request with the task and its day, for Ava's box", () => {
  const fill = (language) => (key, values) => text[language][key].replace(/\{(\w+)\}/g, (_, name) => values[name]);
  const item = { title: "Email", date: "2026-10-02", status: "planned" };
  assert.equal(askMoveText(item, fill("en"), "en"), "Move “Email” from Fri 2 Oct to today");
  assert.equal(askMoveText(item, fill("zh"), "zh"), "把“Email”从10月2日周五移到今天");
});

test("a project's status is on track, stalled for its idle days, paused, or without steps", () => {
  assert.equal(projectStatusText({ health: "on-track", idleDays: 2 }, t), "projectOnTrack");
  assert.equal(projectStatusText({ health: "stalled", idleDays: 3 }, t), 'projectStalled {"days":3}');
  assert.equal(projectStatusText({ health: "paused", idleDays: null }, t), "pausedLabel");
  assert.equal(projectStatusText({ health: "no-steps", idleDays: 1 }, t), "projectNoSteps");
});

test("each kind of agent note has its own icon, and low energy alone is worded", () => {
  assert.deepEqual(["slipping", "length-off", "due-for-review", "stalled", "low-energy", "low-energy-full",
    "doubt-usual-time", "doubt-too-short"].map(noteIcon), ["history", "clock", "book", "pause", "sun", "sun", "clock", "clock"]);
  assert.equal(noteIcon("day-wont-fit"), noteIcon("anything else"));
  assert.equal(noticeText({ kind: "low-energy", values: { energy: 2 } }, t, "en"), 'avaNoticeLowEnergy {"energy":2}');
  assert.ok(text.en.avaNoticeLowEnergy && text.zh.avaNoticeLowEnergy);
});

test("a bar's time is short enough to sit above it, and a day with none shows a dash", () => {
  assert.deepEqual([45, 60, 90, 125, 0].map(barTime), ["45m", "1h", "1h30", "2h05", "–"]);
});

test("lists over days are grouped by day, in order, leaving out days with nothing", () => {
  const items = [{ id: "a", date: "2026-10-07" }, { id: "b", date: "2026-10-05" }, { id: "c", date: "2026-10-07" }];
  assert.deepEqual(byDay(items).map((group) => [group.date, group.items.map((item) => item.id)]),
    [["2026-10-05", ["b"]], ["2026-10-07", ["a", "c"]]]);
});

test("every card's empty state says how to fill it: through + Add at the top, or with its own link that adds nothing", () => {
  const cards = ["today", "todayPast", "notes", "subjects", "practice", "habits", "energy", "load", "meetings", "carryOvers",
    "projects", "nextSteps", "recentDone", "library"];
  assert.deepEqual(Object.keys(EMPTY_STATES).sort(), [...cards].sort());
  for (const [card, { text: key, action }] of Object.entries(EMPTY_STATES)) {
    assert.ok(text.en[key] && text.zh[key], `${card}: ${key}`);
    if (action) assert.ok(text.en[action] && text.zh[action], `${card}: ${action}`);
  }
  assert.deepEqual(Object.entries(EMPTY_STATES).filter(([, state]) => state.action).map(([card, state]) => [card, state.action]),
    [["todayPast", "areaSeeAll"], ["notes", "areaAskAva"], ["energy", "areaReportEnergy"], ["carryOvers", "areaSeeAll"],
      ["recentDone", "areaSeeAll"]]);
  assert.deepEqual([text.en.useAddHint, Boolean(text.zh.useAddHint)], ["Use + Add to add one.", true]);
});

test("an area page has one add button, at the top, whose menu adds a task, a goal, or a note or file", () => {
  const screen = readFileSync(new URL("../src/records/AreaScreen.jsx", import.meta.url), "utf8");
  const cards = readFileSync(new URL("../src/records/AreaCards.jsx", import.meta.url), "utf8");
  assert.deepEqual(AREA_ADD_CHOICES.map(([choice]) => choice), ["task", "goal", "note"]);
  for (const [, key] of AREA_ADD_CHOICES) assert.ok(text.en[key] && text.zh[key], key);
  assert.deepEqual(AREA_ADD_CHOICES.map(([, key]) => text.en[key]), ["Task", "Goal", "Note or file"]);
  assert.equal((screen.match(/<ActionMenu\b/g) || []).length, 1);
  assert.doesNotMatch(cards, /name="plus"|onAddTask|onNewGoal|canAdd|addAction|addTaskAction/);
  assert.deepEqual([text.en.noSessionPlanned, text.en.noNextStep], ["No session planned", "No next step yet"]);
});

test("an area is one page: no tab list, and the day's task list is drawn once", () => {
  const screen = readFileSync(new URL("../src/records/AreaScreen.jsx", import.meta.url), "utf8");
  const cards = readFileSync(new URL("../src/records/AreaCards.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(screen, /role="tablist"|role="tab"|AREA_TABS|tabOverview|tabTasks/);
  assert.equal(text.en.tabOverview, undefined);
  assert.equal((`${screen}${cards}`.match(/className="dw-area-tasks"/g) || []).length, 1);
});

test("See all opens Tasks, or the Library, with its area switch set to the area", () => {
  const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
  assert.match(app, /onSeeAll=\{\(\) => navigate\("tasks", activeTab\)\}/);
  assert.match(app, /<TasksScreen key=\{listArea\}[^>]*initialArea=\{listArea\}/);
  assert.match(app, /onSeeLibrary=\{\(\) => navigate\("library", activeTab\)\}/);
  assert.match(app, /<LibraryScreen key=\{listArea\}[^>]*initialArea=\{listArea\}/);
});

test("done means fully done on the area cards: partly done counts in no figure, and no caption says otherwise", () => {
  const cards = readFileSync(new URL("../src/records/AreaCards.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(cards, /"partial"\]\)/);
  assert.equal(text.en.recentDoneCounts, "Project tasks done in the 7 days to this day, newest first.");
  for (const key of AREA_SCREEN_TEXT) assert.doesNotMatch(text.en[key], /done or partly done/i, key);
});

test("every text the area screens use exists in both languages", () => {
  for (const key of AREA_SCREEN_TEXT) assert.ok(text.en[key] && text.zh[key], key);
});
