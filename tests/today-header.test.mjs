import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const screen = readFileSync(new URL("../src/today/TodayScreen.jsx", import.meta.url), "utf8");
const header = screen.slice(screen.indexOf('<header className="dw-page-head dw-today-head">'), screen.indexOf("</header>"));

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
