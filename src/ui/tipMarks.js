/**
 * Which of a graph's marks a key moves to: the arrow keys go one mark on, or in a grid one row up or down;
 * Home and End go to the first and last; Escape hides the tip. From no mark, any move starts at the first.
 * @param {string} key - The key pressed, as KeyboardEvent names it.
 * @param {number} index - The mark the tip is on, or -1 for none.
 * @param {number} count - How many marks the graph has.
 * @param {number} [columns=0] - The marks in a row of a grid, or 0 for a single row of marks.
 * @returns {number|null} The mark to show, -1 to hide the tip, or null for a key the graph leaves to the page.
 */
export function moveMark(key, index, count, columns = 0) {
  if (key === "Escape") return -1;
  const row = columns || 1;
  const step = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: row, ArrowUp: -row }[key];
  if (step === undefined && key !== "Home" && key !== "End") return null;
  if (!count) return null;
  if (index < 0) return 0;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  const next = index + step;
  return next < 0 || next >= count ? index : next;
}

/**
 * A mark's tip: the same words as its accessible name, or for a part with none, the words it was given.
 * @param {{dataset: object, getAttribute: (name: string) => string|null}} mark - A graph's mark.
 * @returns {string} What its tip says.
 */
export function markText(mark) {
  return mark.dataset.tip || mark.getAttribute("aria-label") || "";
}
