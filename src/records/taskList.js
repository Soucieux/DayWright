import { formatMinutes, timeRange } from "../time.js";
import { timeTaken } from "./timeTaken.js";

/** Days back the Tasks list reaches; those days are history. */
export const PAST_DAYS = 14;

/** Days ahead the Tasks list reaches. */
export const AHEAD_DAYS = 60;

/**
 * What a Tasks list shows, in one area or all, with agent suggestions still waiting left to Calendar: its tasks, and
 * their dates, those from today on in the order they came, then the past ones, newest first.
 * @param {object[]} items - The tasks across the list's days, in date order.
 * @param {string} area - "all", or the one area shown.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @returns {{shown: object[], upcoming: string[], past: string[]}} The tasks shown, and their dates.
 */
export function taskDays(items, area, today) {
  const shown = items
    .filter((item) => item.acceptance !== "pending")
    .filter((item) => area === "all" || item.domain === area);
  const dates = [...new Set(shown.map((item) => item.date))];
  return { shown, upcoming: dates.filter((date) => date >= today), past: dates.filter((date) => date < today).reverse() };
}

/**
 * What a Tasks row's time column shows: when it runs, "19:00–19:30", or null for a task with no start; its length
 * under it, "30 min"; an estimated length marked ≈ on its end and its length, "09:30–≈10:15" and "≈45 min"; and for a
 * past task, the time it took once its status set one, unless that was none, as for a task skipped as it began.
 * @param {{date: string, start_time: string|null, duration_minutes: number, durationSource?: string}} item - The task;
 *   see `timeTaken` for the time it took.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @param {string} language - `en` or `zh`.
 * @returns {{range: string|null, length: string, took: string|null}} The column's lines, worded.
 */
export function taskTimeCell(item, today, language) {
  const mark = item.durationSource === "estimate" ? "≈" : "";
  const [start, end] = item.start_time ? timeRange(item.start_time, item.duration_minutes).split("–") : [];
  const taken = item.date < today ? timeTaken(item) : null;
  return { range: item.start_time ? `${start}–${mark}${end}` : null,
    length: `${mark}${formatMinutes(item.duration_minutes, language)}`,
    took: taken?.minutes > 0 ? formatMinutes(taken.minutes, language) : null };
}
