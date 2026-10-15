/** How far each arrow key moves along a tab list. */
const TAB_STEPS = { ArrowRight: 1, ArrowLeft: -1 };

/**
 * The tab an arrow key moves to from the one chosen, wrapping at either end, as a tab list does.
 * @param {string[]} ids - The tabs' ids, in order.
 * @param {string} current - The chosen tab's id.
 * @param {string} key - The key pressed.
 * @returns {string|null} The tab to move to, or null for a key that moves nothing.
 */
export function tabAfter(ids, current, key) {
  const step = TAB_STEPS[key];
  if (!step) return null;
  return ids[(ids.indexOf(current) + step + ids.length) % ids.length];
}
