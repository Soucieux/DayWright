/**
 * Where each key moves along a tab list, from the tab at `place` of `count`: ← and → to the one before or after,
 * round either end, and Home and End to the first and the last.
 */
const TAB_KEYS = {
  ArrowRight: (place, count) => (place + 1) % count,
  ArrowLeft: (place, count) => (place - 1 + count) % count,
  Home: () => 0,
  End: (place, count) => count - 1,
};

/**
 * The tab a key moves to from the one chosen, as a tab list's keys do (see TAB_KEYS).
 * @param {string[]} ids - The tabs' ids, in order.
 * @param {string} current - The chosen tab's id.
 * @param {string} key - The key pressed.
 * @returns {string|null} The tab to move to, or null for a key that moves nothing.
 */
export function tabAfter(ids, current, key) {
  const move = TAB_KEYS[key];
  if (!move) return null;
  return ids[move(ids.indexOf(current), ids.length)];
}
