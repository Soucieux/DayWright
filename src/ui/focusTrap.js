/** What can take focus inside a panel, in the order Tab moves through it: a tab list's other tabs wait. */
export const FOCUSABLE = ["button", "input", "select", "textarea"].map((tag) => `${tag}:not([disabled]):not([tabindex='-1'])`)
  .concat("a[href]", "[tabindex]:not([tabindex='-1'])").join(", ");

/**
 * The control Tab or Shift+Tab reaches next inside a centred panel, wrapping round at either end so focus never leaves
 * it. The panel moves focus itself, buttons included, as WebKit's own Tab skips them.
 * @param {number} count - How many controls the panel holds.
 * @param {number} at - The focused one's place among them, or -1 for none.
 * @param {boolean} backwards - Whether Shift is held.
 * @returns {number|null} The place to move to, or null with nothing to focus.
 */
export function nextFocus(count, at, backwards) {
  if (!count) return null;
  if (at === -1) return backwards ? count - 1 : 0;
  return (at + (backwards ? count - 1 : 1)) % count;
}
