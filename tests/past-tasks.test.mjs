import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { goalTaskAction, stillLinkedKeys } from "../src/records/goalTasks.js";
import { refusalKey } from "../src/serviceText.js";
import { noticeText } from "../src/talk/notices.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const t = (key, values = {}) => text.en[key].replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));

test("a goal's task list offers Delete on a past task and Edit on today's and later ones", () => {
  const today = "2026-10-03";
  assert.equal(goalTaskAction({ date: "2026-10-02" }, today), "delete");
  assert.equal(goalTaskAction({ date: today }, today), "edit");
  assert.equal(goalTaskAction({ date: "2026-10-04" }, today), "edit");
});

test("a goal that can't be removed yet names one linked task or several", () => {
  assert.deepEqual(stillLinkedKeys(1), { body: "goalStillLinkedOne", action: "showLinkedTaskOne" });
  assert.deepEqual(stillLinkedKeys(3), { body: "goalStillLinked", action: "showLinkedTasks" });
  assert.equal(text.en.goalStillLinkedOne, "1 task is still linked to it. Delete it from this goal's task list, or unlink it from the goal (for a past task, ask Ava), then try again.");
  assert.equal(text.zh.goalStillLinkedOne, "仍有 1 个任务关联到它。请在这个目标的任务列表中删除它，或取消它与目标的关联（过去的任务请告诉 Ava），然后再试。");
  assert.equal(text.en.goalStillLinked, "{count} tasks are still linked to it. Delete them from this goal's task list, or unlink them from the goal (for past tasks, ask Ava), then try again.");
  assert.equal(text.zh.goalStillLinked, "仍有 {count} 个任务关联到它。请在这个目标的任务列表中删除它们，或取消它们与目标的关联（过去的任务请告诉 Ava），然后再试。");
  assert.deepEqual([text.en.showLinkedTaskOne, text.zh.showLinkedTaskOne], ["Show the linked task", "查看这个关联任务"]);
  assert.deepEqual([text.en.showLinkedTasks, text.zh.showLinkedTasks], ["Show the {count} linked tasks", "查看 {count} 个关联任务"]);
  assert.deepEqual([text.en.cantRemoveGoal, text.zh.cantRemoveGoal], ["Can't remove this goal yet", "暂时无法移除这个目标"]);
  assert.deepEqual([text.en.nothingWasRemoved, text.zh.nothingWasRemoved], ["Nothing was removed.", "没有移除任何内容。"]);
});

test("a past day's banner says it is read-only, then that Ava changes its tasks", () => {
  assert.deepEqual([text.en.readOnlyPastDay, text.en.readOnlyPastBody], ["Read-only · past day", "You can view this day and its plan, not change them."]);
  assert.deepEqual([text.zh.readOnlyPastDay, text.zh.readOnlyPastBody], ["只读 · 已过去的日期", "你可以查看这一天及其计划，但不能更改。"]);
  assert.deepEqual([text.en.pastDayAskAva, text.zh.pastDayAskAva], ["To change or remove a task, ask Ava.", "如需更改或移除任务，请告诉 Ava。"]);
  assert.ok(text.en.pastDayNoPlan && text.zh.pastDayNoPlan);
});

test("a goal's list and the Tasks screen say a past task changes through Ava", () => {
  assert.deepEqual([text.en.goalPastTaskNote, text.zh.goalPastTaskNote], ["To change a past task, ask Ava.", "要更改过去的任务，请告诉 Ava。"]);
  assert.equal(text.en.tasksRangeNote, "Showing the last {past} days and the next {ahead}. A past task can be changed only through Ava; agent suggestions wait in Calendar.");
  assert.equal(text.zh.tasksRangeNote, "显示过去 {past} 天和未来 {ahead} 天。过去的任务只能通过 Ava 更改；智能体建议在日历中等待你决定。");
});

test("no screen still says a past task is edited from Goals", () => {
  for (const language of ["en", "zh"]) {
    for (const [key, message] of Object.entries(text[language])) {
      assert.doesNotMatch(message, /from Goals|edited from (its|that) goal|在“目标”中/, `${language}.${key}`);
    }
  }
});

test("the Tasks screen has no goal filter", () => {
  const screen = readFileSync(new URL("../src/records/TasksScreen.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(screen, /onClearGoal|linkedToGoal|showAllTasks|goalId === goal/);
  assert.equal(text.en.linkedToGoal, undefined);
  assert.equal(text.en.showAllTasks, undefined);
});

test("a direct change to a past task is refused in the interface's own words, in both languages", () => {
  assert.equal(refusalKey("A past task changes only through Ava; ask Ava to change it"), "pastTaskThroughAva");
  assert.equal(refusalKey("Daily item not found"), null);
  assert.deepEqual([text.en.pastTaskThroughAva, text.zh.pastTaskThroughAva],
    ["A past task changes only through Ava. Ask Ava to change it.", "过去的任务只能通过 Ava 更改。请告诉 Ava 要改什么。"]);
});

test("a past plan's entry whose task was removed is marked Removed in both languages", () => {
  assert.deepEqual([text.en.entryRemoved, text.zh.entryRemoved], ["Removed", "已移除"]);
});

test("Ava asks which task a change to a past day means when it names none", () => {
  assert.equal(noticeText({ kind: "clarify-past-task", values: { date: "2026-10-01" } }, t, "en"),
    "Which task on Thursday 1 October do you mean? I couldn't find it among that day's tasks; say its name as it appears in the list.");
});
