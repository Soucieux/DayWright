import assert from "node:assert/strict";
import test from "node:test";
import { goalSpan } from "../src/records/goalSpan.js";
import { clockOfTimestamp, dateTime } from "../src/time.js";

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);

test("a goal's span runs from when it was made to the end its tasks' lengths give it, in local time", () => {
  const goal = { startAt: "2026-10-03T08:00:00+00:00", endAt: "2026-10-04T09:45:00+00:00" };
  assert.equal(goalSpan(goal, t, "en"),
    `goalSpan ${JSON.stringify({ from: dateTime(goal.startAt, "en"), to: dateTime(goal.endAt, "en") })}`);
});

test("a goal that starts and ends on one day names that day once", () => {
  const goal = { startAt: "2026-10-03T14:00:00+00:00", endAt: "2026-10-03T14:45:00+00:00" };
  assert.equal(goalSpan(goal, t, "en"),
    `goalSpanSameDay ${JSON.stringify({ from: dateTime(goal.startAt, "en"), to: clockOfTimestamp(goal.endAt) })}`);
});

test("a date and time read in the interface language, to the minute", () => {
  const moment = new Date("2026-10-03T08:05:00+00:00");
  const clock = `${String(moment.getHours()).padStart(2, "0")}:${String(moment.getMinutes()).padStart(2, "0")}`;
  assert.ok(dateTime("2026-10-03T08:05:00+00:00", "en").endsWith(clock));
  assert.ok(dateTime("2026-10-03T08:05:00+00:00", "zh").includes(clock));
});
