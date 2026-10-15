import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const screen = readFileSync(new URL("../src/today/TodayScreen.jsx", import.meta.url), "utf8");
const header = screen.slice(screen.indexOf('<header className="dw-page-head dw-today-head">'), screen.indexOf("</header>"));

test("Paused since stacks under the Reported chip, so pausing never narrows the day strip beside them", () => {
  const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
  assert.match(css, /\n\.dw-today-head \.dw-chips \{ flex-direction: column; align-items: flex-start; \}/);
  const chips = header.slice(header.indexOf('<div className="dw-chips">'), header.indexOf("</div>", header.indexOf('<div className="dw-chips">')));
  assert.ok(chips.indexOf('t("reportedChip")') < chips.indexOf('t("pausedSinceChip"'), "the Reported chip first, Paused since under it");
  // Resume takes Pause's place in the same room, the wider label's, so the actions never widen and narrow the strip.
  assert.match(header, /<PauseLabel shown="resumeDayAction" \/>/);
  assert.match(header, /<PauseLabel shown="pauseDayAction" \/>/);
  assert.match(css, /\n\.dw-pause-label > span \{ grid-area: 1 \/ 1; \}/);
  assert.match(css, /\n\.dw-pause-room \{ visibility: hidden; \}/);
});

test("Today's header holds the energy row, above Add task and Propose plans", () => {
  assert.ok(header.includes("<EnergyRow"), "the energy row is in the header");
  assert.ok(header.indexOf("<EnergyRow") < header.indexOf('className="dw-page-actions"'), "it comes before the buttons");
});

test("the energy row is one line, its short label and the 1–5 scale, with no caption or note in any state", () => {
  const row = screen.slice(screen.indexOf("function EnergyRow"), screen.indexOf("\n}\n", screen.indexOf("function EnergyRow")));
  assert.match(row, /t\("energyLabel"\)/, "it shows the short label, Energy");
  assert.match(row, /<legend className="dw-visually-hidden">\{t\("energyQuestion"\)\}<\/legend>/, "the question stays for screen readers");
  assert.doesNotMatch(screen, /energyLowNote|energyScale|dw-caption">\{level/, "no caption beside or under the scale");
});

test("the energy row shows whether or not the day has tasks, and only once", () => {
  const energy = header.indexOf("<EnergyRow");
  assert.ok(energy >= 0 && energy < header.indexOf("{!empty &&"), "it is in the header, outside the buttons' condition");
  assert.equal((screen.match(/<EnergyRow\b/g) || []).length, 1);
});
