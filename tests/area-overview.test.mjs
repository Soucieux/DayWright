import assert from "node:assert/strict";
import test from "node:test";
import { AREA_MEANINGS, carryOverText, loadBars, streakText } from "../src/records/areaOverview.js";
import { suggestsArea } from "../src/records/taskDraft.js";
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

test("the week's load is drawn against its busiest day", () => {
  assert.deepEqual(loadBars([{ date: "2026-09-28", minutes: 60 }, { date: "2026-09-29", minutes: 120 }, { date: "2026-09-30", minutes: 0 }])
    .map((day) => day.share), [0.5, 1, 0]);
  assert.deepEqual(loadBars([{ date: "2026-09-28", minutes: 0 }]).map((day) => day.share), [0]);
});

test("a carry-over says where a task moved on to, or that it is still not done", () => {
  assert.equal(carryOverText({ title: "Slides", date: "2026-09-30", movedTo: "2026-10-04" }, t, "en"),
    'carryMoved {"from":"Wed 30 Sept","to":"Sun 4 Oct"}');
  assert.equal(carryOverText({ title: "Email", date: "2026-10-02", status: "partial" }, t, "zh"),
    'carryUndone {"date":"10月2日周五","status":"partial"}');
});
