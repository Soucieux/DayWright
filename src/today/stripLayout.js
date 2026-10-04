import { minutesOf } from "../time.js";

/** The frame plans fill, 09:00 to 22:00, in minutes after midnight. */
export const DAY_START_MINUTES = 9 * 60;
export const DAY_END_MINUTES = 22 * 60;
const FRAME_MINUTES = DAY_END_MINUTES - DAY_START_MINUTES;

/** The hours marked under the strip. */
export const HOUR_MARKS = ["09:00", "12:00", "15:00", "18:00", "22:00"];

/** How near the now mark, as a percentage of the strip's width, an hour label gives way to the time now. */
const NOW_CLEAR_PERCENT = 8;

/** Where a stretch of the day falls on the strip, as percentages of its width. */
const place = (start, end) => ({
  left: ((start - DAY_START_MINUTES) / FRAME_MINUTES) * 100,
  width: ((end - start) / FRAME_MINUTES) * 100,
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
 * The hour labels under the strip, leaving room under the now mark for the time now.
 * @param {number} nowAt - Where now falls on the strip, as a percentage of its width.
 * @returns {{clock: string, at: number}[]} Each hour shown, with where it falls along the strip;
 *   an hour within NOW_CLEAR_PERCENT of the now mark is left out.
 */
export function hourMarks(nowAt) {
  return HOUR_MARKS.map((clock) => ({ clock, at: place(DAY_START_MINUTES, minutesOf(clock)).width }))
    .filter(({ at }) => Math.abs(at - nowAt) >= NOW_CLEAR_PERCENT);
}

/**
 * Lay the day's timed tasks, lunch and dinner on a strip from 09:00 to 22:00, and count the time
 * still open before 22:00.
 * @param {object[]} timed - The timed rows, each with `start_time` and `duration_minutes`.
 * @param {number} now - Minutes after midnight now.
 * @param {{title: string, start_time: string, duration_minutes: number}[]} meals - The day's lunch and dinner.
 * @returns {{tasks: object[], meals: object[], nowAt: number, leftMinutes: number, mealMinutes: number,
 *   taskMinutes: number, openMinutes: number}} Each task inside the frame with its row, cut at the
 *   frame's edges; lunch and dinner; where now falls, held at the strip's start before 09:00 and at
 *   its end after 22:00; the minutes from now, or 09:00, to 22:00; and how those split into the
 *   meals still ahead, the tasks' time outside them, and the open time no meal or task takes.
 */
export function dayStrip(timed, now, meals) {
  const spans = timed.map((row) => {
    const start = minutesOf(row.start_time);
    return { row, start: Math.max(start, DAY_START_MINUTES), end: Math.min(start + row.duration_minutes, DAY_END_MINUTES) };
  }).filter(({ start, end }) => end > start);
  const kept = meals.map((meal) => ({ title: meal.title, start: minutesOf(meal.start_time), end: minutesOf(meal.start_time) + meal.duration_minutes }));
  const from = Math.min(Math.max(now, DAY_START_MINUTES), DAY_END_MINUTES);
  // A task paused with its goal is on hold, so its time stays open.
  const paused = (row) => row.source?.goalStatus === "paused";
  const ahead = ({ start, end }) => [Math.max(start, from), end];
  const mealMinutes = coveredMinutes(kept.map(ahead));
  // A task during a meal counts once, as meal time.
  const takenMinutes = coveredMinutes([...spans.filter(({ row }) => !paused(row)), ...kept].map(ahead));
  return {
    tasks: spans.map(({ row, start, end }) => ({ row, paused: paused(row), ...place(start, end) })),
    meals: kept.map(({ title, start, end }) => ({ title, ...place(start, end) })),
    nowAt: place(DAY_START_MINUTES, from).width,
    leftMinutes: DAY_END_MINUTES - from,
    mealMinutes,
    taskMinutes: takenMinutes - mealMinutes,
    openMinutes: DAY_END_MINUTES - from - takenMinutes,
  };
}
