import assert from "node:assert/strict";
import test from "node:test";
import { changeCounts, replacementRows } from "../src/plans/planDiff.js";

/** Build a plan entry with only the fields the comparison reads. */
function entry(id, start, minutes, extra = {}) {
  return { id, title: id, start_time: start, duration_minutes: minutes, completion_status: "planned", source_item_id: `item-${id}`, ...extra };
}

test("names every kind of change between a set plan and its replacement", () => {
  const current = [
    entry("walk", "07:00", 30, { completion_status: "done" }),
    entry("work", "09:00", 180),
    entry("review", "17:30", 30),
    entry("groceries", "18:15", 40),
    entry("study", "19:30", 60),
    entry("reading", "20:30", 30),
  ];
  const next = [
    entry("walk", "07:00", 30, { completion_status: "done" }),
    entry("work", "09:00", 180),
    entry("review", "17:30", 20),
    entry("study", "19:00", 45),
    entry("stretch", "20:00", 20),
    entry("reading", "20:30", 45),
  ];

  const rows = replacementRows(current, next);

  assert.deepEqual(rows.map((row) => [row.kind, (row.before || row.after).id]), [
    ["reported", "walk"], ["same", "work"], ["shorter", "review"], ["removed", "groceries"],
    ["moved", "study"], ["added", "stretch"], ["longer", "reading"],
  ]);
});

test("counts changes separately from entries that stay or were already reported", () => {
  const rows = replacementRows(
    [entry("walk", "07:00", 30, { completion_status: "done" }), entry("work", "09:00", 60), entry("gym", "18:00", 60)],
    [entry("walk", "07:00", 30, { completion_status: "done" }), entry("work", "10:00", 60), entry("nap", "15:00", 20)],
  );

  assert.deepEqual(changeCounts(rows), { changed: 3, reported: 1, byKind: { moved: 1, added: 1, removed: 1 } });
});

test("matches a task scheduled twice to each of its entries in order", () => {
  const current = [entry("a", "09:00", 60, { source_item_id: "client" }), entry("b", "13:30", 60, { source_item_id: "client" })];
  const next = [entry("c", "09:00", 60, { source_item_id: "client" }), entry("d", "14:00", 60, { source_item_id: "client" })];

  assert.deepEqual(replacementRows(current, next).map((row) => [row.kind, row.after?.id]), [["same", "c"], ["moved", "d"]]);
});

test("matches planner-made entries without a task by title", () => {
  const rows = replacementRows(
    [entry("Buffer", "12:00", 15, { source_item_id: null })],
    [entry("Buffer", "12:15", 15, { source_item_id: null })],
  );

  assert.equal(rows.length, 1);
  assert.equal(rows[0].kind, "moved");
});

test("reports no changes for identical plans", () => {
  const plan = [entry("work", "09:00", 60), entry("walk", "12:30", 30)];

  assert.deepEqual(changeCounts(replacementRows(plan, plan.map((item) => ({ ...item })))), { changed: 0, reported: 0, byKind: {} });
});
