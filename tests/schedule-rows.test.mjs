import assert from "node:assert/strict";
import test from "node:test";
import { timeColumn } from "../src/records/taskDraft.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();

test("a meal row's time column shows its start over its length", () => {
  assert.deepEqual(timeColumn({ kind: "meal", title: "Lunch", start_time: "12:00", duration_minutes: 60 }, "en"),
    { start: "12:00", length: "1 h" });
});

test("a task row's time column shows its start over its length, an estimate marked", () => {
  assert.deepEqual(timeColumn({ start_time: "09:30", duration_minutes: 45, durationSource: "estimate" }, "en"),
    { start: "09:30", length: "≈ 45 min" });
  assert.deepEqual(timeColumn({ kind: "entry", start_time: "14:00", duration_minutes: 90, source: { durationSource: "user" } }, "zh"),
    { start: "14:00", length: "1 小时 30 分" });
});

test("a task with no start shows its length alone", () => {
  assert.deepEqual(timeColumn({ start_time: null, duration_minutes: 30 }, "en"), { start: null, length: "30 min" });
});

test("a meal row is named just Lunch or Dinner, in both languages", () => {
  assert.deepEqual([text.en.mealNameLunch, text.en.mealNameDinner], ["Lunch", "Dinner"]);
  assert.deepEqual([text.zh.mealNameLunch, text.zh.mealNameDinner], ["午餐", "晚餐"]);
});
