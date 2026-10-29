import { DAY_MS, localDateOf, localeOf } from "../time.js";

/** Days shown in a month grid: six weeks, Monday first, so every month fits the same grid. */
const GRID_DAYS = 42;

/**
 * List the dates a month grid shows, from the Monday on or before the 1st.
 * @param {string} month - A YYYY-MM month.
 * @returns {string[]} 42 YYYY-MM-DD dates.
 */
export function monthDates(month) {
  const first = new Date(`${month}-01T12:00:00`);
  first.setDate(first.getDate() - ((first.getDay() + 6) % 7));
  return Array.from({ length: GRID_DAYS }, (_, index) => {
    const value = new Date(first);
    value.setDate(first.getDate() + index);
    return localDateOf(value);
  });
}

/**
 * Move a month forward or back.
 * @param {string} month - A YYYY-MM month.
 * @param {number} offset - Months to move; negative moves back.
 * @returns {string} The YYYY-MM month reached.
 */
export function shiftMonth(month, offset) {
  const value = new Date(`${month}-01T12:00:00`);
  value.setMonth(value.getMonth() + offset);
  return localDateOf(value).slice(0, 7);
}

/**
 * Name a month for a heading.
 * @param {string} month - A YYYY-MM month.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "September 2026" or "2026年9月".
 */
export function monthTitle(month, language) {
  return new Intl.DateTimeFormat(localeOf(language), { month: "long", year: "numeric" })
    .format(new Date(`${month}-01T12:00:00`));
}

/**
 * Move a date forward or back by whole days.
 * @param {string} value - A YYYY-MM-DD date.
 * @param {number} days - Days to move; negative moves back.
 * @returns {string} The YYYY-MM-DD date reached.
 */
export function addDays(value, days) {
  const date = new Date(`${value}T12:00:00`);
  date.setDate(date.getDate() + days);
  return localDateOf(date);
}

/**
 * Count whole days from one date to another.
 * @param {string} from - A YYYY-MM-DD date.
 * @param {string} to - A YYYY-MM-DD date.
 * @returns {number} Days from `from` to `to`; negative when `to` is earlier.
 */
export function daysBetween(from, to) {
  return Math.round((new Date(`${to}T12:00:00`) - new Date(`${from}T12:00:00`)) / DAY_MS);
}
