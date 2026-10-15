import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { AVA_GAP, AVA_MARGIN, AVA_SIZE, avaFrame } from "../src/talk/avaFrame.js";
import { starterPrompts } from "../src/talk/starters.js";
import { interfaceText } from "./interfaceText.mjs";

const WIDE = { width: 1412, height: 938 };
const SHEET = 440;

test("Ava offers three starter questions for the place on show, and for Plans its own", () => {
  for (const topic of ["today", "plans", "calendar", "records", "library"]) {
    const keys = starterPrompts(topic);
    assert.equal(keys.length, 3, topic);
    assert.ok(keys.every((key) => key.startsWith("avaStart")), topic);
  }
  assert.ok(starterPrompts("plans").includes("avaStartPlansDiffer"));
  assert.deepEqual(starterPrompts("somewhere new"), starterPrompts("today"));
});

test("Ava is docked at the right, full height: 8 px under the top bar's line, 8 px above the window's bottom", () => {
  assert.deepEqual([AVA_SIZE.width, AVA_MARGIN, AVA_GAP], [540, 12, 8]);
  const BAR = 61;
  for (const [width, height] of [[1440, 900], [1280, 800], [1024, 700]]) {
    assert.deepEqual(avaFrame({ width, height }, 0, BAR), { left: width - 540 - 12, top: BAR + 8, width: 540, height: height - BAR - 16 }, `${width}×${height}`);
  }
  assert.equal(avaFrame({ width: 1440, height: 900 }, 0, 75).top, 83, "the top follows the top bar's measured line");
});

test("with a side panel open she sits just left of it; in a narrow window she narrows to fit", () => {
  assert.equal(avaFrame(WIDE, SHEET, 61).left, WIDE.width - SHEET - 540 - 12);
  assert.deepEqual(avaFrame({ width: 500, height: 700 }, 0, 61), { left: 12, top: 69, width: 476, height: 700 - 61 - 16 });
  assert.equal(avaFrame({ width: 900, height: 700 }, SHEET, 61).left, 12, "never past the window's left edge");
});

test("Ava can't be moved or resized, and what was once remembered is no longer read", () => {
  const panel = readFileSync(new URL("../src/talk/TalkPanel.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(panel, /daywright-ava-position|daywright-ava-height|POSITION_KEY|HEIGHT_KEY|localStorage/);
  assert.doesNotMatch(panel, /dw-talk-resize|onDragStart|onResizeStart|putBack|resetHeight|avaMoveHint|avaResize/);
  assert.match(panel, /const frame = avaFrame\(viewport, sheetWidth, barBottom\);/);
  assert.match(panel, /document\.querySelector\("\.dw-topbar"\)/, "the top bar's line is measured, not assumed");
  assert.match(panel, /<header className="dw-talk-head">/, "the header is no drag handle");
  const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
  assert.doesNotMatch(css, /\.dw-talk-resize|\.dw-talk-head \{[^}]*cursor|\.dw-talk-head:active/);
  assert.match(css, /\.dw-talk-panel \{ position: fixed; inset: 64px 0 0;/, "on a phone she stays the bottom sheet");
  const text = interfaceText();
  for (const language of ["en", "zh"]) assert.equal(text[language].avaMoveHint ?? text[language].avaResize, undefined, language);
});
