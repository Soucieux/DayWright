import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { CLICK_MS, CLICK_PX, closesAva } from "../src/talk/outsideClick.js";

const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const down = (extra = {}) => ({ x: 100, y: 100, at: 1000, onDragRegion: false, ...extra });

test("only a quick, still click outside Ava closes her", () => {
  assert.equal(closesAva(down(), { x: 101, y: 102, at: 1120 }), true, "a click");
  assert.equal(closesAva(down(), { x: 100, y: 100, at: 1500 }), false, "a 500 ms hold");
  assert.equal(closesAva(down(), { x: 110, y: 100, at: 1100 }), false, "a 10 px drag");
  assert.equal(closesAva(down({ onDragRegion: true }), { x: 100, y: 100, at: 1050 }), false, "a press on the window's drag region");
  assert.equal(closesAva(down(), { x: 100, y: 100, at: 1000 + CLICK_MS }), false, "at the limit it's a hold");
  assert.equal(closesAva(down(), { x: 100 + CLICK_PX, y: 100, at: 1050 }), false, "at the limit it's a drag");
});

test("Ava's panel closes by that rule alone, its phone scrim too, and a keyboard click outside still closes her", () => {
  const panel = source("talk/TalkPanel.jsx");
  assert.match(panel, /import \{ closesAva \} from "\.\/outsideClick";/);
  assert.match(panel, /onDragRegion: event\.target instanceof Element && Boolean\(event\.target\.closest\("\[data-tauri-drag-region\]"\)\)/);
  assert.match(panel, /else if \(down && closesAva\(down, \{ x: event\.clientX, y: event\.clientY, at: event\.timeStamp \}\)\) closeRef\.current\(\);/);
  assert.match(panel, /if \(event\.detail === 0\) closeRef\.current\(\);/, "Enter or Space on a button elsewhere");
  assert.match(panel, /<button type="button" className="dw-talk-scrim" hidden=\{!open\} tabIndex=\{-1\} aria-hidden="true" \/>/,
    "the scrim has no click of its own");
});
