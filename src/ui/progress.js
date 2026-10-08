/**
 * The marks the progress graphs draw, worked out from their numbers so each graph's component only
 * lays them out: a period's days with the time fully done by area, each day's share of tasks fully
 * done, how a set plan's entries were followed, and a goal's steps done week by week. Sizes are
 * percentages, as the other visuals use.
 */
import { localDateOf } from "../time.js";
import { datesBetween, percent } from "./visuals.js";

/** Finishing bars need this many days with tasks; fewer is too little to compare. */
export const FINISHING_MIN_DAYS = 2;
/**
 * The parts of a set plan's entries, in the order its bar stacks them, from done at the base: "noReply"
 * for one left without a status once its day's 22:00 passed, "dayPaused" for one left so on a day that
 * ended paused, "unreported" for one today still to do.
 */
export const FOLLOW_PARTS = ["done", "partial", "moved", "skipped", "noReply", "dayPaused", "unreported"];

/**
 * Every day of a period, with what the service counted on it.
 * @param {string} start - The first day, YYYY-MM-DD.
 * @param {string} end - The last day.
 * @param {{date: string, scheduled: number, done: number, minutes: object}[]} days - The days the service
 *   listed; none after today.
 * @returns {{date: string, scheduled: number, done: number, minutes: object}[]} Each day in order, a day
 *   it didn't list counting nothing.
 */
export function padDays(start, end, days) {
  const known = new Map(days.map((day) => [day.date, day]));
  return datesBetween(start, end).map((date) => known.get(date) || { date, scheduled: 0, done: 0, minutes: {} });
}

/**
 * Each day's planned time fully done, stacked by area, against the fullest day.
 * @param {{date: string, minutes: object}[]} days - Each day, with its minutes fully done by area.
 * @param {string[]} areas - The areas in the order they stack, from the base.
 * @returns {{date: string, total: number, height: number, parts: {domain: string, minutes: number,
 *   height: number}[], empty: boolean}[]} Each bar's total and height, and its areas' parts, each as a
 *   share of the fullest day; empty with nothing fully done.
 */
export function areaDayBars(days, areas) {
  const totals = days.map((day) => Object.values(day.minutes || {}).reduce((sum, minutes) => sum + minutes, 0));
  const top = Math.max(0, ...totals);
  return days.map((day, index) => ({
    date: day.date,
    total: totals[index],
    height: top ? percent(totals[index], top) : 0,
    parts: areas.filter((domain) => day.minutes?.[domain]).map((domain) => ({
      domain, minutes: day.minutes[domain], height: percent(day.minutes[domain], top) })),
    empty: !totals[index],
  }));
}

/**
 * Each day's share of its tasks fully done.
 * @param {{date: string, scheduled: number, done: number}[]} days - Each day's tasks and those fully done.
 * @returns {{date: string, scheduled: number, done: number, rate: number|null, height: number,
 *   empty: boolean}[]} Each bar's whole percentage, null and empty on a day with no tasks.
 */
export function finishingBars(days) {
  return days.map(({ date, scheduled, done }) => {
    const rate = scheduled ? Math.round((done / scheduled) * 100) : null;
    return { date, scheduled, done, rate, height: rate ?? 0, empty: !scheduled };
  });
}

/**
 * A period's finishing in all: its days with tasks, the tasks fully done of those scheduled, and
 * whether there are enough days to show.
 * @param {{scheduled: number, done: number}[]} days - Each day's tasks and those fully done.
 * @returns {{days: number, done: number, scheduled: number, rate: number|null, enough: boolean}} The
 *   totals, the whole percentage, and whether FINISHING_MIN_DAYS days have tasks.
 */
export function finishingTotals(days) {
  const withTasks = days.filter((day) => day.scheduled);
  const done = withTasks.reduce((sum, day) => sum + day.done, 0);
  const scheduled = withTasks.reduce((sum, day) => sum + day.scheduled, 0);
  return { days: withTasks.length, done, scheduled, rate: scheduled ? Math.round((done / scheduled) * 100) : null,
    enough: withTasks.length >= FINISHING_MIN_DAYS };
}

/**
 * A set plan's entries as the parts of one bar, in FOLLOW_PARTS order, each as a share of them all.
 * @param {{done: number, partial: number, moved: number, skipped: number, noReply: number, unreported: number}} counts -
 *   The entries in each part.
 * @returns {{total: number, parts: {key: string, count: number, share: number}[]}} Every entry, and
 *   the parts that have any.
 */
export function followThroughParts(counts) {
  const total = FOLLOW_PARTS.reduce((sum, key) => sum + (counts[key] || 0), 0);
  return { total, parts: FOLLOW_PARTS.filter((key) => counts[key]).map((key) => ({ key, count: counts[key],
    share: percent(counts[key], total) })) };
}

/**
 * A period's set plans followed in all.
 * @param {{done: number, partial: number, moved: number, skipped: number, noReply: number, unreported: number}[]} days -
 *   Each day with a set plan.
 * @returns {object} How many days, and the entries in each part over them all.
 */
export function followThroughTotals(days) {
  return { days: days.length, ...Object.fromEntries(FOLLOW_PARTS.map((key) => [key, days.reduce((sum, day) => sum + (day[key] || 0), 0)])) };
}

/**
 * How a day's set plan was followed, from its entries: as each was reported, an entry left without a
 * status once its day's 22:00 passed as no reply, one still to do as not yet reported, and one moved on
 * to another day as moved. Left out, as Summary leaves them out: one for a removed task, and one still to
 * do whose goal is paused.
 * @param {{completion_status: string, removed?: boolean, moved_to?: string|null, source?: {goalStatus?: string, noReply?: boolean}}[]} entries -
 *   The set plan's entries, each with the task it came from.
 * @returns {{done: number, partial: number, moved: number, skipped: number, noReply: number, unreported: number}} The entries in each part.
 */
export function planFollowThrough(entries) {
  const counts = Object.fromEntries(FOLLOW_PARTS.map((key) => [key, 0]));
  for (const entry of entries) {
    if (entry.removed) {
      if (entry.moved_to) counts.moved += 1;
    } else if (entry.completion_status !== "planned") {
      counts[entry.completion_status] += 1;
    } else if (entry.source?.goalStatus !== "paused") {
      counts[entry.source?.dayPaused ? "dayPaused" : entry.source?.noReply ? "noReply" : "unreported"] += 1;
    }
  }
  return counts;
}

/**
 * The Monday of a date's week.
 * @param {string} date - A day, YYYY-MM-DD.
 * @returns {string} Its week's Monday, YYYY-MM-DD.
 */
function mondayOf(date) {
  const day = new Date(`${date}T12:00:00Z`);
  day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
  return day.toISOString().slice(0, 10);
}

/**
 * A day some days after another.
 * @param {string} date - A day, YYYY-MM-DD.
 * @param {number} count - How many days later.
 * @returns {string} That day, YYYY-MM-DD.
 */
function daysAfter(date, count) {
  const day = new Date(`${date}T12:00:00Z`);
  day.setUTCDate(day.getUTCDate() + count);
  return day.toISOString().slice(0, 10);
}

/**
 * A goal's burn-up: a column for each week, Monday to Sunday, from the week it was made, or of its
 * first step if earlier, to this week or that of its last step. Up to this week a column holds the
 * steps fully done so far; this week and every week ahead add, outlined, the steps planned through
 * them. A past step never reported is neither done nor ahead; every step counts toward the total.
 * @param {{date: string, status: string}[]} items - The goal's tasks, its steps.
 * @param {string} startAt - When the goal was made, an ISO timestamp.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @returns {{weeks: {start: string, done: number|null, planned: number, current: boolean, future: boolean}[],
 *   total: number, done: number, ahead: number, through: string|null}} The weeks, null done on a week
 *   ahead; the steps in all, done so far, and planned after today, with the last such day.
 */
export function goalBurnup(items, startAt, today) {
  if (!items.length) return { weeks: [], total: 0, done: 0, ahead: 0, through: null };
  const dates = items.map((item) => item.date).sort();
  const thisWeek = mondayOf(today);
  const doneBy = (end) => items.filter((item) => item.status === "done" && item.date <= end).length;
  const aheadBy = (end) => items.filter((item) => item.status === "planned" && item.date > today && item.date <= end).length;
  const weeks = [];
  const last = mondayOf([today, dates[dates.length - 1]].sort()[1]);
  for (let start = mondayOf([localDateOf(startAt), dates[0]].sort()[0]); start <= last; start = daysAfter(start, 7)) {
    const end = daysAfter(start, 6);
    const done = doneBy(end < today ? end : today);
    const current = start === thisWeek;
    const future = start > thisWeek;
    weeks.push({ start, done: future ? null : done, planned: done + (current || future ? aheadBy(end) : 0), current, future });
  }
  const ahead = items.filter((item) => item.status === "planned" && item.date > today).map((item) => item.date).sort();
  return { weeks, total: items.length, done: doneBy(today), ahead: ahead.length, through: ahead[ahead.length - 1] ?? null };
}
