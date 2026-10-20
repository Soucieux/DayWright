import { clockOf, minutesOf } from "../time.js";

/** Your day until it is set in Settings › Schedule: plans fill it, and the strip draws it. */
export const DEFAULT_DAY = { start: "09:00", end: "22:00" };

/** Hours between the marks under the strip, from Your day's start; the last full mark keeps two hours before its end. */
const MARK_HOURS = 3;
const LAST_MARK_GAP_MINUTES = 2 * 60;

/** How near the now mark, as a percentage of the strip's width, an hour label gives way to the time now. */
const NOW_CLEAR_PERCENT = 8;

/**
 * Your day as the strip's frame, in minutes after midnight.
 * @param {{start: string, end: string}} [day=DEFAULT_DAY] - Your day, as the local service gives it.
 * @returns {{start: number, end: number}} Its start and end.
 */
export function dayFrame(day = DEFAULT_DAY) {
  return { start: minutesOf(day.start), end: minutesOf(day.end) };
}

/** Where a stretch of the day falls on a strip of `frame`, as percentages of its width. */
const place = (frame, start, end) => ({
  left: ((start - frame.start) / (frame.end - frame.start)) * 100,
  width: ((end - start) / (frame.end - frame.start)) * 100,
});

/**
 * Minutes covered by stretches of time, counting an overlap once.
 * @param {[number, number][]} spans - Start and end minutes.
 * @returns {number} The minutes at least one stretch covers.
 */
function coveredMinutes(spans) {
  let covered = 0;
  let reached = -Infinity;
  for (const [start, end] of [...spans].sort((a, b) => a[0] - b[0])) {
    const from = Math.max(start, reached);
    if (end > from) covered += end - from;
    reached = Math.max(reached, end);
  }
  return covered;
}

/**
 * The hour labels under the strip, leaving room under the now mark for the time now: Your day's start, every
 * MARK_HOURS hours from it while LAST_MARK_GAP_MINUTES remain before its end, and its end.
 * @param {number} nowAt - Where now falls on the strip, as a percentage of its width.
 * @param {{start: string, end: string}} [day=DEFAULT_DAY] - Your day.
 * @returns {{clock: string, at: number}[]} Each hour shown, with where it falls along the strip;
 *   an hour within NOW_CLEAR_PERCENT of the now mark is left out.
 */
export function hourMarks(nowAt, day = DEFAULT_DAY) {
  const frame = dayFrame(day);
  const marks = [];
  for (let minute = frame.start; minute <= frame.end - LAST_MARK_GAP_MINUTES; minute += MARK_HOURS * 60) marks.push(minute);
  return [...marks, frame.end].map((minute) => ({ clock: clockOf(minute), at: place(frame, frame.start, minute).width }))
    .filter(({ at }) => Math.abs(at - nowAt) >= NOW_CLEAR_PERCENT);
}

/**
 * Lay the day's timed tasks, lunch and dinner on a strip across Your day, and count the time still
 * open before it ends.
 * @param {object[]} timed - The timed rows, each with `start_time` and `duration_minutes`.
 * @param {number} now - Minutes after midnight now.
 * @param {{title: string, start_time: string, duration_minutes: number}[]} meals - The day's lunch and dinner.
 * @param {{area?: string|null, day?: {start: string, end: string}}} [options] - With an area, only that area's
 *   tasks are drawn and counted, as an area's own strip shows them; the meals stay. `day` is Your day,
 *   DEFAULT_DAY until set.
 * @returns {{tasks: object[], meals: object[], nowAt: number, leftMinutes: number, mealMinutes: number,
 *   taskMinutes: number, openMinutes: number}} Each task inside the frame with its row, cut at the
 *   frame's edges; lunch and dinner; where now falls, held at the strip's start before Your day starts
 *   and at its end after it ends; the minutes from now, or its start, to its end; and how those split
 *   into the meals still ahead, the tasks' time outside them, and the open time no meal or task takes.
 */
export function dayStrip(timed, now, meals, { area = null, day = DEFAULT_DAY } = {}) {
  const frame = dayFrame(day);
  const spans = timed.filter((row) => !area || row.domain === area).map((row) => {
    const start = minutesOf(row.start_time);
    return { row, start: Math.max(start, frame.start), end: Math.min(start + row.duration_minutes, frame.end) };
  }).filter(({ start, end }) => end > start);
  const kept = meals.map((meal) => ({ title: meal.title, start: minutesOf(meal.start_time), end: minutesOf(meal.start_time) + meal.duration_minutes }));
  const from = Math.min(Math.max(now, frame.start), frame.end);
  // A task paused with its goal is on hold, so its time stays open.
  const paused = (row) => row.source?.goalStatus === "paused";
  const ahead = ({ start, end }) => [Math.max(start, from), end];
  const mealMinutes = coveredMinutes(kept.map(ahead));
  // A task during a meal counts once, as meal time.
  const takenMinutes = coveredMinutes([...spans.filter(({ row }) => !paused(row)), ...kept].map(ahead));
  return {
    tasks: spans.map(({ row, start, end }) => ({ row, paused: paused(row), ...place(frame, start, end) })),
    meals: kept.map(({ title, start, end }) => ({ title, ...place(frame, start, end) })),
    nowAt: place(frame, frame.start, from).width,
    leftMinutes: frame.end - from,
    mealMinutes,
    taskMinutes: takenMinutes - mealMinutes,
    openMinutes: frame.end - from - takenMinutes,
  };
}
