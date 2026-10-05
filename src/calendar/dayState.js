import { shortDate } from "../time.js";

/**
 * The mark a past plan's entry carries once its task left the day: "Moved to {day}" when it moved
 * forward, else "Removed"; none while the task is still there.
 * @param {{removed?: boolean, moved_to?: string|null}} entry - A plan's entry.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string|null} The mark, or null.
 */
export function historyMark(entry, t, language) {
  if (!entry.removed) return null;
  return entry.moved_to ? t("entryMovedTo", { day: shortDate(entry.moved_to, language) }) : t("entryRemoved");
}

/**
 * The entries a day's counts take: a past plan's entry for a removed task stays on show, marked
 * Removed, but is left out of the counts.
 * @param {{removed?: boolean}[]} entries - The day's plan entries.
 * @returns {object[]} The entries that count, in the order given.
 */
export function countedEntries(entries) {
  return entries.filter((entry) => !entry.removed);
}

/**
 * Read what a calendar cell shows from the month's record for its date. Nothing is estimated: a
 * date without a record is empty, and a past date is read-only.
 * @param {object|undefined} record - The date's record from the local service, if it has one.
 * @param {string} date - The cell's YYYY-MM-DD date.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @returns {{past: boolean, empty: boolean, set: boolean, recorded: boolean, done: number,
 *   total: number, presets: number, suggested: number}} Whether a plan was set and how much of it was
 *   reported done; whether the day was recorded without a set plan; and, ahead of time, how many
 *   commitments are preset and how many agent suggestions wait for the user.
 */
export function dayState(record, date, today) {
  const past = date < today;
  const future = date > today;
  const set = Boolean(record?.confirmed);
  return {
    past,
    empty: !record,
    set,
    recorded: Boolean(record) && !set && !future && Boolean(record.managedCount || record.planSource),
    done: set ? record.doneCount || 0 : 0,
    total: set ? record.entryCount || 0 : 0,
    presets: future && record ? record.managedCount || 0 : 0,
    suggested: record?.suggestedCount || 0,
  };
}
