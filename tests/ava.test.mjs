import assert from "node:assert/strict";
import test from "node:test";
import { AVA_MARGIN, AVA_MIN_HEIGHT, AVA_SIZE, avaFrame } from "../src/talk/avaFrame.js";
import { starterPrompts } from "../src/talk/starters.js";

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

test("Ava opens in the bottom-right corner, its full size, without moving the page", () => {
  assert.deepEqual(avaFrame(WIDE, null, 0), {
    left: WIDE.width - AVA_SIZE.width - AVA_MARGIN, top: WIDE.height - AVA_SIZE.height - AVA_MARGIN, ...AVA_SIZE,
  });
});

test("with a sheet open, Ava sits just left of it unless it was moved", () => {
  assert.equal(avaFrame(WIDE, null, SHEET).left, WIDE.width - SHEET - AVA_SIZE.width - AVA_MARGIN);
  assert.equal(avaFrame(WIDE, { left: 200, top: 120 }, SHEET).left, 200);
});

test("a moved Ava stays where it was put, but always inside the window", () => {
  assert.deepEqual(avaFrame(WIDE, { left: 200, top: 120 }, 0), { left: 200, top: 120, ...AVA_SIZE });
  const outside = avaFrame(WIDE, { left: 5000, top: -40 }, 0);
  assert.equal(outside.left, WIDE.width - AVA_SIZE.width - AVA_MARGIN);
  assert.equal(outside.top, AVA_MARGIN);
});

test("Ava keeps a small gap from the window's edges", () => {
  assert.equal(AVA_MARGIN, 12);
});

test("a height the user chose is kept, above a minimum and within the window", () => {
  const tall = avaFrame(WIDE, null, 0, 760);
  assert.equal(tall.height, 760);
  assert.equal(tall.top, WIDE.height - 760 - AVA_MARGIN);
  assert.equal(avaFrame(WIDE, null, 0, 100).height, AVA_MIN_HEIGHT);
  assert.equal(avaFrame({ width: 1412, height: 500 }, null, 0, 760).height, 500 - 2 * AVA_MARGIN);
});

test("in a short window Ava is shorter, so it never leaves the screen", () => {
  const frame = avaFrame({ width: 1412, height: 500 }, null, 0);
  assert.equal(frame.height, 500 - 2 * AVA_MARGIN);
  assert.equal(frame.top, AVA_MARGIN);
});
