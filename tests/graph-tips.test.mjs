import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { markText, moveMark } from "../src/ui/tipMarks.js";

const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
/** One component's code, from its declaration to the next exported one. */
const component = (code, name) => {
  const start = code.indexOf(`export function ${name}(`);
  const next = code.indexOf("\nexport function", start + 1);
  return code.slice(start, next < 0 ? undefined : next);
};

test("arrow keys move between a graph's marks, Home and End go to its ends, and Escape hides the tip", () => {
  assert.equal(moveMark("ArrowRight", 0, 7), 1);
  assert.equal(moveMark("ArrowRight", 6, 7), 6, "the last stays the last");
  assert.equal(moveMark("ArrowLeft", 0, 7), 0);
  assert.equal(moveMark("ArrowDown", 2, 7), 3, "in a row of bars, down is the next");
  assert.equal(moveMark("ArrowDown", 2, 28, 14), 16, "in a grid, down is a row down");
  assert.equal(moveMark("ArrowUp", 2, 28, 14), 2, "the top row stays");
  assert.equal(moveMark("Home", 5, 7), 0);
  assert.equal(moveMark("End", 1, 7), 6);
  assert.equal(moveMark("Escape", 3, 7), -1);
  assert.equal(moveMark("Enter", 3, 7), null, "any other key is left to the page");
  assert.equal(moveMark("ArrowRight", -1, 7), 0, "from no mark, the first");
  assert.equal(moveMark("ArrowRight", 0, 0), null, "a graph with no marks moves nowhere");
});

test("a tip says the same words as its mark's label, or the words a part without one is given", () => {
  const mark = (label, tip) => ({ dataset: tip ? { tip } : {}, getAttribute: (name) => (name === "aria-label" ? label : null) });
  assert.equal(markText(mark("Fri 10:00–11:00 · 3 tasks finished")), "Fri 10:00–11:00 · 3 tasks finished");
  assert.equal(markText(mark(null, "Done 4")), "Done 4");
});

test("every existing graph shows tips: done by area, finishing, follow-through, the burn-up and the area pages' bars", () => {
  const graphs = source("ui/ProgressGraphs.jsx");
  for (const name of ["DoneByArea", "FinishingBars", "FollowThroughBar", "FollowThroughDays", "GoalBurnup"]) {
    assert.match(component(graphs, name), /<GraphTips /, name);
    assert.match(component(graphs, name), /data-mark/, name);
  }
  assert.match(component(graphs, "FollowThroughBar"), /data-tip=/, "a follow-through part has words of its own");
  const visuals = source("ui/AreaVisuals.jsx");
  for (const name of ["LoadBars", "EnergyBars"]) {
    assert.match(component(visuals, name), /<GraphTips /, name);
    assert.match(component(visuals, name), /data-mark/, name);
  }
});

test("a tip adds to the words: each graph is one tab stop, its marks keep their labels, and focus is announced", () => {
  const tips = source("ui/GraphTips.jsx");
  assert.match(tips, /tabIndex=\{0\}/);
  assert.match(tips, /aria-live="polite"/);
  assert.match(tips, /className="dw-tip"[^>]*aria-hidden="true"/);
  assert.match(source("bench.css"), /\.dw-tip \{[^}]*background: var\(--dw-ink\)/);
});
