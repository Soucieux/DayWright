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
