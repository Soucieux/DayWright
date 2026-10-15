import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { balanceColumns, columnPlaces } from "../src/records/areaOverview.js";

const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const css = source("bench.css");
const GAP = 20;

/** How far apart two columns end, for cards of these heights on these sides: a card of no height takes no gap. */
function spread(heights, sides) {
  const column = (side) => {
    const shown = heights.filter((height, index) => height > 0 && sides[index] === side);
    return shown.reduce((sum, height) => sum + height, 0) + GAP * Math.max(0, shown.length - 1);
  };
  return Math.abs(column(0) - column(1));
}

/** Every way of splitting the cards into two columns, each in page order, the first card on the left. */
function everySplit(count) {
  return Array.from({ length: 2 ** Math.max(0, count - 1) }, (_, mask) =>
    Array.from({ length: count }, (__, index) => (index === 0 ? 0 : (mask >> (index - 1)) & 1)));
}

test("the columns split the cards so their heights come as close as any split keeping page order can", () => {
  let seed = 7;
  const next = () => { seed = (seed * 48271) % 2147483647; return seed; };
  for (let round = 0; round < 300; round += 1) {
    const count = 1 + (next() % 7);
    // Heights as cards have them, some drawing nothing.
    const heights = Array.from({ length: count }, () => (next() % 5 === 0 ? 0 : 60 + (next() % 900) + (next() % 100) / 100));
    const sides = balanceColumns(heights, GAP);
    const closest = Math.min(...everySplit(count).map((split) => spread(heights, split)));
    assert.equal(sides.length, count);
    assert.ok(sides.every((side) => side === 0 || side === 1));
    assert.equal(Math.round(spread(heights, sides)), Math.round(closest), `heights ${heights.join(", ")}`);
  }
});

test("Today is always first in the left column", () => {
  assert.deepEqual(balanceColumns([100, 500, 100], GAP), [0, 1, 0]);
  assert.deepEqual(balanceColumns([900, 100, 100, 100], GAP), [0, 1, 1, 1]);
  assert.deepEqual(balanceColumns([300], GAP), [0]);
  assert.deepEqual(balanceColumns([], GAP), []);
});

test("between equally close splits, the one moving the fewest cards wins, then the one closest to alternating", () => {
  // Four cards alike, nothing placed yet: every two-and-two split ties, and alternating wins.
  assert.deepEqual(balanceColumns([100, 100, 100, 100], GAP), [0, 1, 0, 1]);
  // Already two and two, though not alternating: it stays as it is.
  assert.deepEqual(balanceColumns([100, 100, 100, 100], GAP, [0, 0, 1, 1]), [0, 0, 1, 1]);
  // Today and one card against the other three ties four ways; from where the cards stood, two of those move one
  // card each, and of the two, the one closer to alternating wins.
  const heights = [200, 100, 100, 100, 100];
  assert.deepEqual(balanceColumns(heights, GAP, [0, 0, 0, 1, 1]), [0, 1, 0, 1, 1]);
  assert.equal(spread(heights, [0, 1, 0, 1, 1]), 20);
  // A card that draws nothing goes where it moves least, then alternates; it changes no height.
  assert.deepEqual(balanceColumns([300, 0, 300], GAP), [0, 1, 1]);
  assert.deepEqual(balanceColumns([300, 0, 300], GAP, [0, 0, 1]), [0, 0, 1]);
});

test("the cards change columns only when the new split ends more than one gap closer, so small changes never make them hop", () => {
  // Best is the second card on the left, 70 px apart; the third on the left is 90 px apart, within a gap: it stays.
  assert.deepEqual(balanceColumns([200, 90, 100, 120], GAP), [0, 0, 1, 1]);
  assert.deepEqual(balanceColumns([200, 90, 100, 120], GAP, [0, 1, 0, 1]), [0, 1, 0, 1]);
  // The fourth on the left is 130 px apart, 60 more than the best: it moves.
  assert.deepEqual(balanceColumns([200, 90, 100, 120], GAP, [0, 1, 1, 0]), [0, 0, 1, 1]);
  // A card growing by 5 px, as while its text changes, would tip the best split elsewhere; the cards stay.
  const placed = balanceColumns([200, 100, 100, 100], GAP);
  assert.deepEqual(placed, [0, 1, 0, 1]);
  assert.notDeepEqual(balanceColumns([200, 100, 105, 100], GAP), placed);
  assert.deepEqual(balanceColumns([200, 100, 105, 100], GAP, placed), placed);
  // A card new to the page has no place yet, so the page takes the best split.
  assert.deepEqual(balanceColumns([200, 90, 100, 120], GAP, [0, 1, 0, undefined]), [0, 0, 1, 1]);
});

test("each column stacks its cards from the top with the usual gap, and the shorter one's last card stretches to end level", () => {
  assert.deepEqual(columnPlaces([100, 50, 0, 80], [0, 1, 0, 1], GAP), { tops: [0, 0, 120, 70], height: 150, stretch: { index: 0, by: 50 } });
  assert.deepEqual(columnPlaces([100, 200, 80], [0, 1, 0], GAP), { tops: [0, 0, 120], height: 200, stretch: null });
  assert.deepEqual(columnPlaces([100, 30, 50], [0, 1, 1], GAP), { tops: [0, 0, 50], height: 100, stretch: null });
  assert.deepEqual(columnPlaces([100, 30, 0], [0, 1, 1], GAP), { tops: [0, 0, 50], height: 100, stretch: { index: 1, by: 70 } });
  assert.deepEqual(columnPlaces([240], [0], GAP), { tops: [0], height: 240, stretch: null });
});

test("the area page keeps its cards in one list, ordered left column then right, each placed where its split puts it", () => {
  const screen = source("records/AreaScreen.jsx");
  const columns = screen.slice(screen.indexOf("function AreaColumns"), screen.indexOf("\n}\n", screen.indexOf("function AreaColumns")));
  assert.match(screen, /<AreaColumns>\s*<TodayCard/, "every card of the page goes through the columns, in its order");
  // One list, so a card that changes columns is moved, not made again, and keeps what it had open.
  assert.doesNotMatch(columns, /dw-area-column/);
  assert.match(columns, /<div key=\{card\.key\} className="dw-area-slot" data-slot=\{card\.key\}/);
  assert.match(columns, /balanceColumns\(/);
  assert.match(columns, /columnPlaces\(/);
  // Measured and placed before anything is drawn, and again whenever a card's size changes.
  assert.match(columns, /useLayoutEffect\(/);
  assert.match(columns, /new ResizeObserver\(/);
  assert.match(columns, /flushSync\(/);
  // A card moved to the other column keeps the keyboard's place.
  assert.match(columns, /\.focus\(\{ preventScroll: true \}\)/);
});

test("on a phone the cards make one column, in their order", () => {
  const screen = source("records/AreaScreen.jsx");
  assert.match(screen, /const phone = useViewport\(\)\.width <= PHONE_WIDTH;/);
  assert.match(css, /@media \(max-width: 640px\) \{[^}]*\.dw-area-grid \{ grid-template-columns: 1fr; \}/);
  // Ava, docked since v6.3, needs no phone width of her own: on a phone the same 640 px rule makes her a bottom sheet.
  assert.doesNotMatch(source("talk/TalkPanel.jsx"), /PHONE_WIDTH|\b640\b/);
  assert.match(source("ui/viewport.js"), /export const PHONE_WIDTH = 640;/);
});

test("wider than a phone each card stands at its own place in its column, and a card that draws nothing takes none", () => {
  assert.match(css, /\.dw-area-slot:empty \{ display: none; \}/);
  assert.match(css, /@media \(min-width: 641px\) \{\s*\.dw-area-slot \{ position: absolute; left: 0; width: calc\(\(100% - var\(--dw-area-gap\)\) \/ 2\); \}\s*\.dw-area-slot\[data-side="1"\] \{ left: calc\(\(100% \+ var\(--dw-area-gap\)\) \/ 2\); \}\s*\}/);
  assert.doesNotMatch(css, /\.dw-area-column/);
  // A card that grows keeps its content at its top: its links are no longer pushed to its bottom.
  assert.doesNotMatch(css + source("records/AreaCards.jsx"), /dw-area-card-actions/);
});
