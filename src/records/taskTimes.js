import { clockOf, minutesOf } from "../time.js";

/** Start times are offered on the quarter hour, the grid plans place tasks on. */
const START_STEP_MINUTES = 15;
const MINUTES_PER_DAY = 24 * 60;
/** Lunch and dinner, which every plan keeps free, so no task is fixed over them. */
export const MEALS = [{ title: "Lunch", start: "12:00", minutes: 60 }, { title: "Dinner", start: "18:00", minutes: 60 }];

/**
 * The day's tasks that already take a time: accepted ones with a start time, other than the task
 * being edited, which never clashes with itself.
 * @param {object[]} tasks - The day's tasks.
 * @param {string|null} editingId - The task being edited, or null for a new one.
 * @returns {object[]} The tasks a fixed start time must not overlap.
 */
export function timedTasks(tasks, editingId) {
  return tasks.filter((task) => task.start_time && (task.acceptance ?? "accepted") === "accepted" && task.id !== editingId);
}

/**
 * What stops a task from starting at a time: another task it would overlap, lunch or dinner, or
 * midnight.
 * @param {string} start - The HH:MM start.
 * @param {number} minutes - How long the task lasts.
 * @param {object[]} timed - The tasks that already take a time, from `timedTasks`.
 * @returns {{task: object}|{meal: {title: string, start: string, minutes: number}}|{midnight: true}|null}
 *   The clash, or null when the time is free.
 */
export function startClash(start, minutes, timed) {
  const begin = minutesOf(start);
  if (begin + minutes > MINUTES_PER_DAY) return { midnight: true };
  const overlaps = (other, length) => minutesOf(other) < begin + minutes && begin < minutesOf(other) + length;
  const task = timed.find((other) => overlaps(other.start_time, other.duration_minutes));
  if (task) return { task };
  const meal = MEALS.find((other) => overlaps(other.start, other.minutes));
  return meal ? { meal } : null;
}

/**
 * Every start time the form offers, each with what would stop it. A stored start off the quarter
 * hour is offered too, so an existing task keeps its time.
 * @param {number} minutes - How long the task lasts.
 * @param {object[]} timed - The tasks that already take a time.
 * @param {string|null} current - The start time chosen now.
 * @returns {{time: string, clash: object|null}[]} The times in order.
 */
export function startOptions(minutes, timed, current) {
  const times = Array.from({ length: MINUTES_PER_DAY / START_STEP_MINUTES }, (_, index) => clockOf(index * START_STEP_MINUTES));
  const offered = current && !times.includes(current) ? [...times, current].sort() : times;
  return offered.map((time) => ({ time, clash: startClash(time, minutes, timed) }));
}

/**
 * The first free start at or after a time, or else the first free one that day.
 * @param {string} from - The HH:MM time to look from.
 * @param {number} minutes - How long the task lasts.
 * @param {object[]} timed - The tasks that already take a time.
 * @returns {string|null} A free HH:MM start, or null when none is left that day.
 */
export function firstFreeStart(from, minutes, timed) {
  const free = startOptions(minutes, timed, null).filter((option) => !option.clash);
  return (free.find((option) => minutesOf(option.time) >= minutesOf(from)) || free[0])?.time ?? null;
}
