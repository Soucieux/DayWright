import assert from "node:assert/strict";
import test from "node:test";
import { firstFreeStart, startClash, startOptions, timedTasks } from "../src/records/taskTimes.js";

/** A stored task with only the fields the start-time list reads. */
function task(id, start, minutes = 60, acceptance = "accepted") {
  return { id, title: id, start_time: start, duration_minutes: minutes, acceptance };
}

test("only accepted tasks with a start time, other than the one being edited, take a time", () => {
  const tasks = [task("Stand-up", "10:00"), task("Read", null), task("Suggested", "12:00", 60, "pending"), task("Mine", "14:00")];
  assert.deepEqual(timedTasks(tasks, "Mine").map((item) => item.id), ["Stand-up"]);
});

test("a start clashes when the task would overlap another or run past midnight", () => {
  const timed = [task("Stand-up", "10:00", 60)];
  assert.equal(startClash("09:30", 30, timed), null);
  assert.equal(startClash("09:45", 30, timed).task.id, "Stand-up");
  assert.equal(startClash("10:45", 30, timed).task.id, "Stand-up");
  assert.equal(startClash("11:00", 30, timed), null);
  assert.deepEqual(startClash("23:45", 30, []), { midnight: true });
});

test("the list offers every quarter hour, marks the taken ones, and keeps a stored time off the grid", () => {
  const options = startOptions(30, [task("Stand-up", "10:00", 60)], "08:10");
  assert.equal(options.length, 97);
  assert.deepEqual(options.filter((option) => option.clash?.task).map((option) => option.time), ["09:45", "10:00", "10:15", "10:30", "10:45"]);
  assert.ok(options.some((option) => option.time === "08:10"));
});

test("lunch and dinner take their hour, so no task is fixed over them", () => {
  assert.deepEqual(startClash("11:45", 30, []), { meal: { title: "Lunch", start: "12:00", minutes: 60 } });
  assert.equal(startClash("17:30", 45, []).meal.title, "Dinner");
  assert.equal(startClash("13:00", 30, []), null);
  assert.equal(startClash("11:30", 30, []), null);
  assert.equal(firstFreeStart("12:00", 30, []), "13:00");
});

test("a fixed task taking a taken time moves to the next free one, or the first of the day", () => {
  const timed = [task("Stand-up", "09:00", 60), task("Lunch", "22:00", 120)];
  assert.equal(firstFreeStart("09:00", 30, timed), "10:00");
  assert.equal(firstFreeStart("22:30", 30, timed), "00:00");
});
