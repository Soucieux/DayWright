// How short and how still a press outside Ava must be to close her: a hold, a drag, or a press on the window's drag
// region, as moving the window starts with, never does.
export const CLICK_MS = 300;
export const CLICK_PX = 4;

/**
 * Whether a press outside Ava closes her: a quick, still click, not a hold, a drag or a press on the window's drag
 * region.
 * @param {{x: number, y: number, at: number, onDragRegion: boolean}} down - Where and when it went down, and whether on
 *   the window's drag region.
 * @param {{x: number, y: number, at: number}} up - Where and when it came up, as its click.
 * @returns {boolean}
 */
export function closesAva(down, up) {
  return !down.onDragRegion && up.at - down.at < CLICK_MS && Math.hypot(up.x - down.x, up.y - down.y) < CLICK_PX;
}
