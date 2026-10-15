/** Ava's space from the window's right edge, and from the left when the window is narrow, in CSS pixels. */
export const AVA_MARGIN = 12;
/** Ava's space under the top bar's line and above the window's bottom edge. */
export const AVA_GAP = 8;
/** Ava's width when the window has room for it; wide enough for three suggested questions in a row. */
export const AVA_SIZE = { width: 540 };

/**
 * Where Ava sits: docked at the right, just left of a side panel open there, from 8 px under the top bar's line to
 * 8 px above the window's bottom, so her height follows the window's. She is narrower when the window is, and never
 * leaves it. She can't be moved or resized. On a phone she is a bottom sheet instead (see bench.css).
 * @param {{width: number, height: number}} viewport - The window's size.
 * @param {number} sheetWidth - The width of a side panel open at the window's right, or 0.
 * @param {number} barBottom - Where the top bar's line is, from the window's top.
 * @returns {{left: number, top: number, width: number, height: number}} Ava's frame.
 */
export function avaFrame(viewport, sheetWidth, barBottom) {
  const width = Math.min(AVA_SIZE.width, viewport.width - 2 * AVA_MARGIN);
  const top = barBottom + AVA_GAP;
  const left = Math.max(AVA_MARGIN, viewport.width - width - AVA_MARGIN - sheetWidth);
  return { left, top, width, height: viewport.height - top - AVA_GAP };
}
