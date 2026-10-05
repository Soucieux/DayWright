import assert from "node:assert/strict";
import test from "node:test";
import { barMarks, dayDots, habitSquares, practiceDots, stepSegments, weekdayLetters } from "../src/ui/visuals.js";

const WEEK = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-10", "2026-10-11"];

test("load bars stand against the busiest day, with the done part inside each planned bar", () => {
  const { bars, guideAt } = barMarks([{ date: WEEK[0], value: 90, done: 60 }, { date: WEEK[1], value: 45, done: 45 },
    { date: WEEK[2], value: 0, done: 0 }]);
  assert.deepEqual(bars.map((bar) => [bar.height, bar.doneHeight, bar.empty]), [[100, 67, false], [50, 50, false], [0, 0, true]]);
  assert.equal(guideAt, null);
});

test("a done part never stands taller than its planned bar", () => {
  const [bar] = barMarks([{ date: WEEK[0], value: 30, done: 45 }]).bars;
  assert.equal(bar.doneHeight, bar.height);
});

test("energy bars run 1 to 5, with a guide at 2 and low readings marked", () => {
  const { bars, guideAt } = barMarks([{ date: WEEK[0], value: 3 }, { date: WEEK[1], value: null }, { date: WEEK[2], value: 2 },
    { date: WEEK[3], value: 5 }], { max: 5, guide: 2, low: 2 });
  assert.deepEqual(bars.map((bar) => [bar.height, bar.low, bar.empty]), [[60, false, false], [0, false, true], [40, true, false], [100, false, false]]);
  assert.equal(guideAt, 40);
});

test("a week with nothing in it draws empty bars", () => {
  const { bars } = barMarks(WEEK.map((date) => ({ date, value: 0, done: 0 })));
  assert.equal(bars.length, 7);
  assert.ok(bars.every((bar) => bar.height === 0 && bar.doneHeight === 0 && bar.empty));
});

test("a habit's week grid marks each day's state, ✗ on a missed day and a faint · on a day its rule skips", () => {
  assert.deepEqual(habitSquares(["done", "partial", "missed", "upcoming", "off", "upcoming", "off"]).map((square) => [square.state, square.symbol]),
    [["done", ""], ["partial", ""], ["missed", "✗"], ["upcoming", ""], ["off", "·"], ["upcoming", ""], ["off", "·"]]);
});

test("practice dots read ● practised, ○ planned but not done, and · nothing planned", () => {
  assert.deepEqual(practiceDots(["practised", "planned", "none", "none", "planned", "none", "practised"]).map((dot) => dot.symbol),
    ["●", "○", "·", "·", "○", "·", "●"]);
});

test("a project's step bar has one segment per step, filled only once fully done", () => {
  const segments = stepSegments([{ id: "a", title: "Draft", status: "done" }, { id: "b", title: "Polish", status: "partial" },
    { id: "c", title: "Ship", status: "planned" }, { id: "d", title: "Test", status: "skipped" }]);
  assert.equal(segments.length, 4);
  assert.deepEqual(segments.map((segment) => segment.filled), [true, false, false, false]);
  assert.deepEqual(stepSegments([]), []);
});

test("the seven-day dot row grows a day's dot with its items, up to three", () => {
  const items = [{ date: WEEK[1] }, { date: WEEK[2] }, { date: WEEK[2] }, ...Array.from({ length: 5 }, () => ({ date: WEEK[4] }))];
  assert.deepEqual(dayDots(WEEK, items).map((dot) => [dot.count, dot.size]),
    [[0, 0], [1, 1], [2, 2], [0, 0], [5, 3], [0, 0], [0, 0]]);
  assert.ok(dayDots(WEEK, []).every((dot) => dot.size === 0));
});

test("weekday letters run Monday to Sunday in either language", () => {
  assert.deepEqual(weekdayLetters(WEEK, "en"), ["M", "T", "W", "T", "F", "S", "S"]);
  assert.deepEqual(weekdayLetters(WEEK, "zh"), ["一", "二", "三", "四", "五", "六", "日"]);
});
