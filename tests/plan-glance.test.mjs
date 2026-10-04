import assert from "node:assert/strict";
import test from "node:test";
import { planGlance } from "../src/plans/planGlance.js";

/** A stored task with only the fields a plan's glance reads. */
function task(id, start, minutes = 60) {
  return { id, title: id, start_time: start, duration_minutes: minutes, acceptance: "accepted" };
}

/** A plan's entry for a task. */
function entry(source, start, minutes = 60) {
  return { id: `entry-${source}`, title: source, source_item_id: source, start_time: start, duration_minutes: minutes };
}

test("a plan's glance names its first task, when it ends, and the lengths it changed", () => {
  const tasks = [task("Stand-up", "07:30", 30), task("Guide", null, 60), task("Walk", null, 30)];
  const glance = planGlance([entry("Walk", "18:30", 30), entry("Stand-up", "07:30", 30), entry("Guide", "08:00", 45)], tasks);
  assert.deepEqual(glance, {
    first: { title: "Stand-up", start: "07:30" }, doneBy: "19:00",
    resized: [{ title: "Guide", from: 60, to: 45 }],
  });
});

test("a plan holding only fixed tasks starts with the first of them, and an empty plan with none", () => {
  assert.deepEqual(planGlance([entry("Stand-up", "10:00", 30)], [task("Stand-up", "10:00", 30)]),
    { first: { title: "Stand-up", start: "10:00" }, doneBy: "10:30", resized: [] });
  assert.deepEqual(planGlance([], []), { first: null, doneBy: null, resized: [] });
});
