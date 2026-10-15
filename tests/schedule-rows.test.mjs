import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { timeColumn } from "../src/records/taskDraft.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
const rule = (selector) => css.match(new RegExp(`(?:^|\\n)${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} \\{([^}]*)\\}`))?.[1] ?? "";

test("a row's title and time sit centred on its status control, in every place such a row is", () => {
  assert.match(rule(".dw-row-block"), /align-items: center;/, "Today's Schedule and Untimed");
  assert.match(rule(".dw-row-time"), /align-content: center;/);
  assert.doesNotMatch(rule(".dw-row-time"), /padding-top/, "with no top padding pushing the time down");
  assert.match(rule(".dw-catch-up-task"), /align-items: center;/, "catch-up");
  for (const [selector, place] of [[".dw-day-row", "Calendar's day rows, Tasks, area cards and a goal's tasks"],
    [".dw-set-row", "Settings"], [".dw-folder-row", "the Library's folders"]]) {
    assert.match(rule(selector), /align-items: center;/, place);
  }
  assert.match(css, /\.dw-sources-table th, \.dw-sources-table td \{[^}]*vertical-align: middle;/, "the Library's items");
  assert.match(rule(".dw-row-rule-note"), /align-items: flex-start;/, "a rule's note keeps its icon at its first line");
});

test("a meal row's time column shows its start over its length", () => {
  assert.deepEqual(timeColumn({ kind: "meal", title: "Lunch", start_time: "12:00", duration_minutes: 60 }, "en"),
    { start: "12:00", length: "1 h" });
});

test("a task row's time column shows its start over its length, an estimate marked", () => {
  assert.deepEqual(timeColumn({ start_time: "09:30", duration_minutes: 45, durationSource: "estimate" }, "en"),
    { start: "09:30", length: "≈45 min" });
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
