import assert from "node:assert/strict";
import test from "node:test";
import { dayRows } from "../src/today/dayRows.js";
import { MIN_TASK_MINUTES, linkableGoals, newTaskDate, taskDraft, taskLength, taskPayload } from "../src/records/taskDraft.js";

/** Build a stored task with only the fields the day's rows read. */
function item(id, start, extra = {}) {
  return { id, title: id, start_time: start, duration_minutes: 45, completion_status: "planned", acceptance: "accepted", ...extra };
}

test("keeps tasks without a start time apart from the timed schedule", () => {
  const day = { confirmedVariantId: null, entries: [], dayItems: [item("read", null), item("call", "14:00"), item("gym", "09:00"), item("idea", null, { acceptance: "pending" })] };
  const { rows, timed, untimed, suggestions } = dayRows(day);
  assert.deepEqual(timed.map((row) => row.id), ["gym", "call"]);
  assert.deepEqual(untimed.map((row) => row.id), ["read"]);
  assert.deepEqual(rows.map((row) => row.id), ["gym", "call", "read"]);
  assert.deepEqual(suggestions.map((row) => row.id), ["idea"]);
});

test("a set plan's placed entry takes the timed schedule from its untimed task", () => {
  const day = {
    confirmedVariantId: "plan",
    entries: [{ id: "entry", title: "read", start_time: "10:15", duration_minutes: 45, completion_status: "planned", source_item_id: "read" }],
    dayItems: [item("read", null)],
  };
  const { timed, untimed } = dayRows(day);
  assert.deepEqual(timed.map((row) => [row.kind, row.start_time]), [["entry", "10:15"]]);
  assert.equal(untimed.length, 0);
});

test("a set plan keeps its lunch and dinner on the schedule, apart from the tasks", () => {
  const day = {
    confirmedVariantId: "plan",
    variants: [{ id: "plan", meals: [{ title: "Lunch", start_time: "12:00", duration_minutes: 60 }] }],
    entries: [{ id: "entry", title: "read", start_time: "13:00", duration_minutes: 45, completion_status: "planned", source_item_id: "read" }],
    dayItems: [item("read", null)],
  };
  const { rows, meals } = dayRows(day);
  assert.deepEqual(meals.map((meal) => [meal.kind, meal.title, meal.start_time]), [["meal", "Lunch", "12:00"]]);
  assert.deepEqual(rows.map((row) => row.kind), ["entry"]);
  assert.deepEqual(dayRows({ ...day, confirmedVariantId: null }).meals, []);
});

test("a new task has no length until the user gives one, and only a fixed task sends a start time", () => {
  const draft = taskDraft(null, "2026-10-02");
  assert.equal(draft.durationMinutes, "");
  assert.equal(draft.constraintKind, "flexible");
  assert.equal(taskPayload(draft).durationMinutes, null);
  assert.equal(taskPayload({ ...draft, durationMinutes: "45" }).durationMinutes, 45);
  assert.equal(taskPayload(draft).startTime, null);
  assert.equal(taskPayload({ ...draft, constraintKind: "fixed", startTime: "08:30" }).startTime, "08:30");
});

test("a task links to active goals in its area, and keeps its own goal while that is paused", () => {
  const goals = [{ id: "spanish", domain: "learning", status: "active" }, { id: "piano", domain: "learning", status: "paused" },
    { id: "garden", domain: "life", status: "active" }];
  assert.deepEqual(linkableGoals(goals, "learning").map((goal) => goal.id), ["spanish"]);
  assert.deepEqual(linkableGoals(goals, "learning", "piano").map((goal) => goal.id), ["spanish", "piano"]);
});

test("saving the task form sends no status, so an outcome reported meanwhile stays", () => {
  const done = item("read", "09:00", { date: "2026-10-02", completion_status: "done" });
  assert.equal("status" in taskPayload(taskDraft(done, "2026-10-02")), false);
  assert.equal("status" in taskPayload(taskDraft(null, "2026-10-02")), false);
});

test("an estimated length stays the agent's until the user gives one; a length given is at least the minimum", () => {
  const estimated = item("read", null, { duration_minutes: 40, durationSource: "estimate", estimatedBy: "learning" });
  assert.equal(taskDraft(estimated, "2026-10-02").durationMinutes, "");
  assert.equal(taskDraft({ ...estimated, durationSource: "user" }, "2026-10-02").durationMinutes, 40);
  assert.equal(MIN_TASK_MINUTES, 30);
});

test("a length an agent estimated reads as approximate, on a task or on its plan entry", () => {
  const estimated = item("read", null, { duration_minutes: 40, durationSource: "estimate" });
  assert.equal(taskLength(estimated, "en"), "≈ 40 min");
  assert.equal(taskLength({ kind: "entry", duration_minutes: 25, source: estimated }, "zh"), "≈ 25 分钟");
  assert.equal(taskLength({ ...estimated, durationSource: "user" }, "en"), "40 min");
});

test("a new task starts today unless a later day is on show", () => {
  assert.equal(newTaskDate("2026-09-20", "2026-10-02"), "2026-10-02");
  assert.equal(newTaskDate("2026-10-02", "2026-10-02"), "2026-10-02");
  assert.equal(newTaskDate("2026-10-09", "2026-10-02"), "2026-10-09");
});
