/**
 * The marks the small visuals draw, worked out from their numbers so each visual's component only
 * lays them out: bars per day, a habit's week grid, practice dots, a project's step bar, a row of
 * seven day dots, and the day's energy as steps, bars and a meter. Sizes are percentages, as the
 * existing tracks and bars use.
 */
import { minutesOf } from "../time.js";

/** The day's average energy at or below which it is low and at or above which it is high, as the service has them. */
export const ENERGY_LOW = 2;
export const ENERGY_HIGH = 4;
/** The levels energy is reported in, 1 to 5. */
export const ENERGY_LEVELS = 5;
/** The part of the day energy's steps are placed in. */
const ENERGY_DAY = ["09:00", "22:00"];

/** The symbol each practice state shows: practised, planned but not done, nothing planned. */
const PRACTICE_SYMBOLS = { practised: "●", planned: "○", none: "·" };
/** The symbol a habit's day shows: ✗ when missed, a faint · when its rule skips the day, else none. */
const HABIT_SYMBOLS = { missed: "✗", off: "·" };
/** The most a day dot grows: one size per item, up to three. */
const MAX_DOT_SIZE = 3;

/**
 * Size a row of bars, one per day, each with the part done inside it, against the largest day.
 * @param {{date: string, value: number|null, done?: number}[]} days - Each day's value, null when it
 *   has none, and how much of it was done.
 * @returns {{date: string, value: number|null, done: number, height: number, doneHeight: number,
 *   empty: boolean}[]} Each bar's height and done height as percentages of the largest, never more
 *   done than planned, and whether it is empty with nothing in it.
 */
export function barMarks(days) {
  const top = Math.max(0, ...days.map((day) => day.value || 0));
  const share = (value) => (top ? Math.round((value / top) * 100) : 0);
  return days.map(({ date, value, done = 0 }) => ({
    date, value, done,
    height: share(value || 0),
    doneHeight: share(Math.min(done, value || 0)),
    empty: !value,
  }));
}

/**
 * A habit's week grid, one square per day from Monday to Sunday.
 * @param {string[]} days - Each day's state: "done", "partial", "missed", "upcoming" or "off".
 * @returns {{state: string, symbol: string}[]} Each square's state, ✗ on a missed day and · on a day the rule skips.
 */
export function habitSquares(days) {
  return days.map((state) => ({ state, symbol: HABIT_SYMBOLS[state] || "" }));
}

/**
 * A subject's practice row, one dot per day from Monday to Sunday.
 * @param {string[]} days - Each day's state: "practised", "planned" or "none".
 * @returns {{state: string, symbol: string}[]} Each day's state and its symbol: ●, ○ or ·.
 */
export function practiceDots(days) {
  return days.map((state) => ({ state, symbol: PRACTICE_SYMBOLS[state] }));
}

/**
 * A project's step bar, one segment per step in the order the steps come.
 * @param {{id: string, title: string, status: string}[]} steps - The project's tasks.
 * @returns {{id: string, title: string, status: string, filled: boolean}[]} Each segment, filled
 *   once its step is fully done; a partly done step stays unfilled.
 */
export function stepSegments(steps) {
  return steps.map(({ id, title, status }) => ({ id, title, status, filled: status === "done" }));
}

/**
 * A row of dots, one per day, each growing with the day's items.
 * @param {string[]} dates - The days, YYYY-MM-DD.
 * @param {{date: string}[]} items - The items, each on its day.
 * @returns {{date: string, count: number, size: number}[]} Each day's count of items and its dot's
 *   size: 0 for none, then one size per item up to MAX_DOT_SIZE.
 */
export function dayDots(dates, items) {
  return dates.map((date) => {
    const count = items.filter((item) => item.date === date).length;
    return { date, count, size: Math.min(count, MAX_DOT_SIZE) };
  });
}

/**
 * The one-letter names of days, as the grids show them beneath their squares.
 * @param {string[]} dates - The days, YYYY-MM-DD.
 * @param {string} language - `en` or `zh`.
 * @returns {string[]} Each day's narrow weekday name, such as M or 一.
 */
export function weekdayLetters(dates, language) {
  const narrow = new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { weekday: "narrow" });
  return dates.map((date) => narrow.format(new Date(`${date}T12:00:00`)));
}

/** A share as a percentage to a tenth, so 3 of 5 reads 60 rather than a float's 60.00000000000001. */
export const percent = (part, whole) => Math.round((part / whole) * 1000) / 10;

/**
 * Every day from one date to another.
 * @param {string} start - The first day, YYYY-MM-DD.
 * @param {string} end - The last day; none when it comes before start.
 * @returns {string[]} The days in order, YYYY-MM-DD.
 */
export function datesBetween(start, end) {
  const dates = [];
  for (const day = new Date(`${start}T12:00:00Z`); day.toISOString().slice(0, 10) <= end; day.setUTCDate(day.getUTCDate() + 1)) {
    dates.push(day.toISOString().slice(0, 10));
  }
  return dates;
}

/**
 * A day's energy as steps: each reading holds its level from its time until the next one, and the
 * last until `until`, placed between 09:00 and 22:00 and by level from 1 at the bottom to 5 at the top.
 * @param {{level: number, time: string}[]} readings - The day's readings, in the order they were made.
 * @param {string} [until="22:00"] - The "HH:MM" the last reading holds to: now on today, 22:00 on another day.
 * @returns {{level: number, time: string, left: number, width: number, bottom: number, low: boolean,
 *   rise: {bottom: number, height: number}|null}[]} Each step's start and length as percentages of the
 *   day, a time outside it at its nearer edge; its height on the scale as a percentage; whether it is
 *   low; and the line up or down to it from the step before, null for the first.
 */
export function energySteps(readings, until = ENERGY_DAY[1]) {
  const [start, end] = ENERGY_DAY.map(minutesOf);
  const across = (time) => percent(Math.min(Math.max(minutesOf(time), start), end) - start, end - start);
  const up = (level) => percent(level - 1, ENERGY_LEVELS - 1);
  return readings.map((reading, index) => {
    const left = across(reading.time);
    const bottom = up(reading.level);
    const before = index ? up(readings[index - 1].level) : null;
    return {
      level: reading.level, time: reading.time, left, bottom, low: reading.level <= ENERGY_LOW,
      width: Math.round((Math.max(left, across(readings[index + 1]?.time ?? until)) - left) * 10) / 10,
      rise: before === null ? null : { bottom: Math.min(before, bottom), height: Math.abs(bottom - before) },
    };
  });
}

/**
 * Days' energy as bars: each day's average out of 5, with a thin line from its lowest to its highest reading.
 * @param {{date: string, average: number|null, low: number|null, high: number|null}[]} days - Each day,
 *   with nulls when none was reported.
 * @returns {{date: string, average: number|null, lowest: number|null, highest: number|null, height: number,
 *   rangeBottom: number, rangeHeight: number, low: boolean, empty: boolean}[]} Each bar's height and its
 *   line's start and length as percentages of 5, whether the day is low, and whether it has no reading.
 */
export function energyBars(days) {
  return days.map(({ date, average, low, high }) => ({
    date, average, lowest: low, highest: high,
    height: average == null ? 0 : percent(average, ENERGY_LEVELS),
    rangeBottom: low == null ? 0 : percent(low, ENERGY_LEVELS),
    rangeHeight: low == null ? 0 : percent(high - low, ENERGY_LEVELS),
    low: average != null && average <= ENERGY_LOW,
    empty: average == null,
  }));
}

/**
 * Every day of a period, with the energy reported on it.
 * @param {string} start - The first day, YYYY-MM-DD.
 * @param {string} end - The last day.
 * @param {{date: string, average: number, low: number, high: number}[]} reported - The days with energy reported.
 * @returns {{date: string, average: number|null, low: number|null, high: number|null}[]} Each day in
 *   order, with nulls for a day with none.
 */
export function periodDays(start, end, reported) {
  const known = new Map(reported.map((day) => [day.date, day]));
  return datesBetween(start, end).map((date) => {
    const found = known.get(date);
    return { date, average: found?.average ?? null, low: found?.low ?? null, high: found?.high ?? null };
  });
}

/**
 * The meter that shows a day's average energy in Calendar: five steps, as many filled as the average
 * rounds to, in the caution colour at ENERGY_LOW or below.
 * @param {number|null} average - The day's average, or null when none was reported.
 * @returns {{steps: boolean[], caution: boolean, empty: boolean}} Whether each step is filled, whether
 *   the meter is in the caution colour, and whether the day has no reading.
 */
export function energyMeter(average) {
  const filled = average == null ? 0 : Math.round(average);
  return { steps: Array.from({ length: ENERGY_LEVELS }, (_, index) => index < filled),
    caution: average != null && average <= ENERGY_LOW, empty: average == null };
}

/**
 * The level of a day's latest reading, which Today's energy row shows as chosen.
 * @param {{level: number}[]|undefined} readings - The day's readings in order.
 * @returns {number|null} The level, or null for a day with none.
 */
export function latestReading(readings) {
  return readings?.length ? readings[readings.length - 1].level : null;
}
