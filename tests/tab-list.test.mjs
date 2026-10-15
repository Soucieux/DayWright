import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { tabAfter } from "../src/ui/tabs.js";

const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("the arrow keys move along a tab list and wrap at its ends; other keys leave it", () => {
  const ids = ["overview", "tasks"];
  assert.equal(tabAfter(ids, "overview", "ArrowRight"), "tasks");
  assert.equal(tabAfter(ids, "tasks", "ArrowRight"), "overview");
  assert.equal(tabAfter(ids, "overview", "ArrowLeft"), "tasks");
  assert.equal(tabAfter(["notes", "plan", "summary"], "plan", "ArrowLeft"), "notes");
  assert.equal(tabAfter(ids, "overview", "Enter"), null);
});

test("one tab list for every page: its tabs with their roles, the chosen one selected and alone in the tab order, the arrow keys moving focus", () => {
  const list = source("ui/TabList.jsx");
  assert.match(list, /className="dw-tabs" role="tablist" aria-label=\{label\}/);
  assert.match(list, /role="tab" id=\{`\$\{idBase\}-tab-\$\{id\}`\}/);
  assert.match(list, /aria-selected=\{selected === id\} aria-controls=\{`\$\{idBase\}-panel`\} tabIndex=\{selected === id \? 0 : -1\}/);
  assert.match(list, /const next = tabAfter\(tabs\.map\(\(\[id\]\) => id\), selected, event\.key\)/);
  assert.match(list, /tabRefs\.current\[next\]\?\.focus\(\)/);
  assert.match(list, /aria-label=\{names\?\.\[id\]\}/, "a tab can carry a name of its own for screen readers, as Folders, 3");
  const side = source("ui/SideTabs.jsx");
  assert.match(side, /<TabList label=\{label\} idBase="dw-side" tabs=\{tabs\} selected=\{currentId\} onSelect=\{setSelected\} \/>/,
    "the side column's tabs use it, as before");
  assert.match(side, /<div id="dw-side-panel" role="tabpanel" aria-labelledby=\{`dw-side-tab-\$\{currentId\}`\} className="dw-column-side">/);
  assert.doesNotMatch(side, /ArrowRight|role="tab"/, "no page keeps its own tab keys");
});
