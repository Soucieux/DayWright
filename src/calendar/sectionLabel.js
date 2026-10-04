import { fullDate, shortDate } from "../time.js";
import { monthTitle } from "./month.js";

/**
 * Name a part of a wider Summary report: a day of a week, a week of a month, or a month of all time.
 * @param {{periodKind: string, periodKey: string, start: string, end: string}} section - The part, as
 *   the local service lists it; a week's key is its ISO week, such as "2026-W40".
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Saturday 3 October", "Week 40 · Mon 28 Sep – Wed 30 Sep" or "September 2026".
 */
export function sectionLabel(section, t, language) {
  if (section.periodKind === "day") return fullDate(section.periodKey, language);
  if (section.periodKind === "week") {
    return t("reportWeekLabel", { week: Number(section.periodKey.split("-W")[1]), from: shortDate(section.start, language),
      to: shortDate(section.end, language) });
  }
  return monthTitle(section.periodKey, language);
}
