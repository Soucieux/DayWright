import assert from "node:assert/strict";
import test from "node:test";
import { DAY_END_MINUTES, DAY_START_MINUTES, dayStrip, hourMarks } from "../src/today/stripLayout.js";
import { formatMinutes } from "../src/time.js";

const FRAME = DAY_END_MINUTES - DAY_START_MINUTES;
const at = (clock) => Number(clock.slice(0, 2)) * 60 + Number(clock.slice(3));
const share = (minutes) => (minutes / FRAME) * 100;
const task = (start, minutes, extra = {}) => ({ id: start, title: start, start_time: start, duration_minutes: minutes,
  domain: "work", completion_status: "planned", ...extra });

test("a task sits on the 09:00–22:00 strip at its time and for its length", () => {
  const [placed] = dayStrip([task("10:00", 30)], at("08:00")).tasks;
  assert.equal(placed.left, share(60));
  assert.equal(placed.width, share(30));
});

test("lunch and dinner are always on the strip, an hour each", () => {
  const { meals } = dayStrip([], at("08:00"));
  assert.deepEqual(meals.map((meal) => [meal.title, meal.left, meal.width]),
    [["Lunch", share(180), share(60)], ["Dinner", share(540), share(60)]]);
});

test("a task running past 22:00 is cut at the edge, and one before 09:00 is left off", () => {
  const { tasks } = dayStrip([task("07:00", 60), task("21:30", 60)], at("08:00"));
  assert.equal(tasks.length, 1);
  assert.equal(tasks[0].width, share(30));
});

test("open time is what is left before 22:00 once meals and timed tasks are taken out", () => {
  assert.equal(dayStrip([task("10:00", 30)], at("08:00")).openMinutes, FRAME - 120 - 30);
  assert.equal(dayStrip([task("13:00", 30)], at("12:30")).openMinutes, at("22:00") - at("12:30") - 30 - 60 - 30);
  assert.equal(dayStrip([task("11:30", 60)], at("08:00")).openMinutes, FRAME - 120 - 30, "an overlap counts once");
});

test("the now marker always shows, held at the strip's ends before 09:00 and after 22:00", () => {
  assert.equal(dayStrip([], at("15:30")).nowAt, share(at("15:30") - DAY_START_MINUTES));
  assert.equal(dayStrip([], at("08:00")).nowAt, 0);
  const late = dayStrip([], at("22:30"));
  assert.equal(late.nowAt, 100);
  assert.equal(late.openMinutes, 0);
});

test("a task paused with its goal stays on the strip but leaves its time open", () => {
  const paused = task("10:00", 60, { source: { goalStatus: "paused" } });
  const { tasks, openMinutes } = dayStrip([paused], at("08:00"));
  assert.equal(tasks.length, 1);
  assert.equal(tasks[0].paused, true);
  assert.equal(openMinutes, FRAME - 120);
});

test("an hour label near the now mark gives way to the time now, and the others stay", () => {
  const clocks = (now) => hourMarks(dayStrip([], at(now)).nowAt).map((mark) => mark.clock);
  assert.deepEqual(clocks("09:34"), ["12:00", "15:00", "18:00", "22:00"]);
  assert.deepEqual(clocks("15:05"), ["09:00", "12:00", "18:00", "22:00"]);
  assert.deepEqual(clocks("13:30"), ["09:00", "12:00", "15:00", "18:00", "22:00"]);
  assert.deepEqual(clocks("23:00"), ["09:00", "12:00", "15:00", "18:00"]);
  assert.equal(hourMarks(50).find((mark) => mark.clock === "22:00").at, 100);
});

test("the time left splits into meals, tasks and open time, which add up to it", () => {
  const strip = dayStrip([task("14:00", 60), task("12:30", 60)], at("10:20"));
  assert.deepEqual([strip.leftMinutes, strip.mealMinutes, strip.taskMinutes, strip.openMinutes], [700, 120, 90, 490]);
  const evening = dayStrip([], at("18:30"));
  assert.deepEqual([evening.mealMinutes, evening.taskMinutes, evening.openMinutes], [30, 0, 180]);
});

test("a length over an hour names its minutes", () => {
  assert.equal(formatMinutes(700, "en"), "11 h 40 min");
  assert.equal(formatMinutes(120, "en"), "2 h");
  assert.equal(formatMinutes(45, "en"), "45 min");
});

test("time left counts from now, or 09:00, to 22:00", () => {
  assert.equal(dayStrip([], at("15:30")).leftMinutes, at("22:00") - at("15:30"));
  assert.equal(dayStrip([], at("08:00")).leftMinutes, FRAME);
  assert.equal(dayStrip([], at("22:30")).leftMinutes, 0);
});
