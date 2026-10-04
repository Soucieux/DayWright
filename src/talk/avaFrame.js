/** Ava's space from the window's edges, in CSS pixels. */
export const AVA_MARGIN = 12;
/** Ava's size when the window has room for it; wide enough for three suggested questions in a row. */
export const AVA_SIZE = { width: 540, height: 600 };
/** The shortest Ava can be made, still showing a reply and the box. */
export const AVA_MIN_HEIGHT = 320;

/**
 * Where Ava's floating window sits. It opens in the bottom-right corner, just left of a sheet that
 * is open there; once moved it stays where it was put. Either way it stays whole inside the window,
 * and is smaller when the window is.
 * @param {{width: number, height: number}} viewport - The window's size.
 * @param {{left: number, top: number}|null} moved - Where the user dragged Ava to, if they did.
 * @param {number} sheetWidth - The width of a sheet open at the window's right, or 0.
 * @param {number} [chosenHeight] - The height the user resized Ava to, if they did.
 * @returns {{left: number, top: number, width: number, height: number}} Ava's frame.
 */
export function avaFrame(viewport, moved, sheetWidth, chosenHeight = AVA_SIZE.height) {
  const width = Math.min(AVA_SIZE.width, viewport.width - 2 * AVA_MARGIN);
  const height = Math.min(Math.max(chosenHeight, AVA_MIN_HEIGHT), viewport.height - 2 * AVA_MARGIN);
  const maxLeft = viewport.width - width - AVA_MARGIN;
  const maxTop = viewport.height - height - AVA_MARGIN;
  const clamp = (value, high) => Math.min(Math.max(value, AVA_MARGIN), high);
  return moved
    ? { left: clamp(moved.left, maxLeft), top: clamp(moved.top, maxTop), width, height }
    : { left: clamp(maxLeft - sheetWidth, maxLeft), top: maxTop, width, height };
}
