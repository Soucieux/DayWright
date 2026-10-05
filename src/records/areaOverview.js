import { shortDate } from "../time.js";

/**
 * Each area's one-line meaning, by its message key, in the order the purpose rule takes them: a task
 * someone else expects is Work, a step toward something with an end is Project, getting better at
 * something is Learning, and everything else is Life.
 */
export const AREA_MEANINGS = {
  work: "areaMeaningWork", project: "areaMeaningProject", learning: "areaMeaningLearning", life: "areaMeaningLife",
};

/**
 * Word a habit's streak: its days done in a row, or its weeks for a weekly repeat.
 * @param {{kind: string, streak: number}} habit - A repeat as Life's overview lists it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} Such as "3 days in a row", or that no streak is running.
 */
export function streakText(habit, t) {
  if (!habit.streak) return t("streakNone");
  return t(habit.kind === "weekly" ? "streakWeeks" : "streakDays", { count: habit.streak });
}

/**
 * Size the week's load by day against its busiest day, for Work's bars.
 * @param {{date: string, minutes: number}[]} load - Each day of the week, with its Work minutes.
 * @returns {{date: string, minutes: number, share: number}[]} Each day with its share of the
 *   busiest day's minutes, 0 to 1; every share is 0 in a week without Work.
 */
export function loadBars(load) {
  const most = Math.max(0, ...load.map((day) => day.minutes));
  return load.map((day) => ({ ...day, share: most ? day.minutes / most : 0 }));
}

/**
 * Say what became of a Work task carried over from the week before.
 * @param {{date: string, movedTo?: string, status?: string}} item - A carry-over as Work's overview
 *   lists it: moved on from a set plan's day (`movedTo`), or still not done on its day (`status`).
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Moved from Wed 30 Sep to Sun 4 Oct".
 */
export function carryOverText(item, t, language) {
  return item.movedTo
    ? t("carryMoved", { from: shortDate(item.date, language), to: shortDate(item.movedTo, language) })
    : t("carryUndone", { date: shortDate(item.date, language), status: t(item.status) });
}
