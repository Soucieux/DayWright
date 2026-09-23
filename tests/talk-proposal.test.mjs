import assert from "node:assert/strict";
import test from "node:test";
import { proposalView } from "../src/talk/proposal.js";

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

test("keeps an unknown proposal's date without guessing what it does", () => {
  assert.deepEqual(proposalView({ actionType: "something_new", payload: { date: "2026-09-25" } }, items), { kind: "other", date: "2026-09-25" });
});
