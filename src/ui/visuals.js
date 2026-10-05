/**
 * The marks the area screens' small visuals draw, worked out from their numbers so each visual's
 * component only lays them out: bars per day, a habit's week grid, practice dots, a project's step
 * bar and a row of seven day dots. Sizes are percentages, as the existing tracks and bars use.
 */

/** The symbol each practice state shows: practised, planned but not done, nothing planned. */
const PRACTICE_SYMBOLS = { practised: "●", planned: "○", none: "·" };
/** The symbol a habit's day shows: ✗ when missed, a faint · when its rule skips the day, else none. */
const HABIT_SYMBOLS = { missed: "✗", off: "·" };
/** The most a day dot grows: one size per item, up to three. */
const MAX_DOT_SIZE = 3;

/**
 * Size a row of bars, one per day, each with the part done inside it.
 * @param {{date: string, value: number|null, done?: number}[]} days - Each day's value, null when it
 *   has none, and how much of it was done.
 * @param {{max?: number, guide?: number, low?: number}} [scale] - The value a full bar stands for
 *   (the largest value when not given), a value to draw a guide line at, and the value at or under
 *   which a bar counts as low.
 * @returns {{bars: {date: string, value: number|null, done: number, height: number, doneHeight: number,
 *   low: boolean, empty: boolean}[], guideAt: number|null}} Each bar's height and done height as
 *   percentages of a full bar, never more done than planned; whether it is low, or empty with
 *   nothing in it; and where the guide falls, as a percentage, or null without one.
 */
export function barMarks(days, { max, guide, low } = {}) {
  const top = max ?? Math.max(0, ...days.map((day) => day.value || 0));
  const share = (value) => (top ? Math.round((value / top) * 100) : 0);
  return {
    bars: days.map(({ date, value, done = 0 }) => ({
      date, value, done,
      height: share(value || 0),
      doneHeight: share(Math.min(done, value || 0)),
      low: low != null && value != null && value <= low,
      empty: !value,
    })),
    guideAt: guide != null && top ? share(guide) : null,
  };
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
