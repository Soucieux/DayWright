import assert from "node:assert/strict";
import test from "node:test";
import { pausedIds, pausedInPlan } from "../src/plans/pausedTasks.js";

const item = (id, goalStatus = null) => ({ id, title: id, goalStatus });
const entry = (id) => ({ id: `entry-${id}`, title: id, source_item_id: id });

test("only a task whose goal is paused counts as paused", () => {
  assert.deepEqual([...pausedIds([item("read", "paused"), item("walk", "active"), item("draft")])], ["read"]);
});

test("a plan names the paused tasks it still holds and those it left out", () => {
  const items = [item("read", "paused"), item("walk", "active"), item("notes", "paused"), item("draft")];

  const { held, left } = pausedInPlan([entry("read"), entry("walk")], items);

  assert.deepEqual(held.map((row) => row.source_item_id), ["read"]);
  assert.deepEqual(left.map((row) => row.id), ["notes"]);
});

test("a plan made after the pause holds no paused task", () => {
  const items = [item("read", "paused"), item("walk")];

  const { held, left } = pausedInPlan([entry("walk")], items);

  assert.deepEqual(held, []);
  assert.deepEqual(left.map((row) => row.id), ["read"]);
});
