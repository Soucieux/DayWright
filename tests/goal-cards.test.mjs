import assert from "node:assert/strict";
import test from "node:test";
import { cardTasks } from "../src/records/goalTasks.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const TODAY = "2026-10-04";

/** A task linked to a goal, as the goal lists it. */
function linked(title, date, startTime = null) {
  return { id: title, title, date, startTime };
}

const titles = (tasks) => tasks.map((task) => task.title);

test("a goal card lists today's and later tasks by date first", () => {
  const card = cardTasks([linked("Old", "2026-09-28"), linked("Later", "2026-10-09"), linked("Today", TODAY, "09:00"),
    linked("Soon", "2026-10-05"), linked("Recent", "2026-10-02")], TODAY);
  assert.deepEqual(titles(card.shown), ["Today", "Soon", "Later"]);
});

test("the most recent past tasks fill up a card with fewer than 3 ahead", () => {
  const card = cardTasks([linked("Old", "2026-09-28"), linked("Recent", "2026-10-02"), linked("Today", TODAY)], TODAY);
  assert.deepEqual(titles(card.shown), ["Today", "Recent", "Old"]);
});

test("a task with no start comes last in its day, ahead and past", () => {
  const ahead = cardTasks([linked("No start", "2026-10-05"), linked("Late", "2026-10-05", "15:00"),
    linked("Early", "2026-10-05", "08:00")], TODAY);
  assert.deepEqual(titles(ahead.shown), ["Early", "Late", "No start"]);
  const past = cardTasks([linked("No start", "2026-10-03"), linked("Morning", "2026-10-03", "08:00"),
    linked("Evening", "2026-10-03", "19:00")], TODAY);
  assert.deepEqual(titles(past.shown), ["Evening", "Morning", "No start"]);
});

test("a card shows at most 3 tasks, and counts them all when there are more", () => {
  const seven = Array.from({ length: 7 }, (_, index) => linked(`Task ${index}`, `2026-10-1${index}`));
  assert.deepEqual(cardTasks(seven, TODAY), { shown: seven.slice(0, 3), total: 7, more: true });
  assert.deepEqual(cardTasks(seven.slice(0, 3), TODAY).more, false);
  assert.deepEqual(cardTasks([], TODAY), { shown: [], total: 0, more: false });
});

test("Show all names how many tasks there are, in both languages", () => {
  assert.deepEqual([text.en.goalShowAll, text.zh.goalShowAll], ["Show all {count} tasks", "查看全部 {count} 个任务"]);
});
