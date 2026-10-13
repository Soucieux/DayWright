import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { SWITCH_POLL_MS, SWITCH_WAIT_MS, switchWorkspace, switchingKey } from "../src/settings/workspaceSwitch.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

/** The service as a switch meets it: each health read gives the next answer, an Error standing for no answer. */
function service(answers) {
  const asked = [];
  const phases = [];
  let clock = 0;
  const io = {
    health: async () => {
      const next = answers.shift();
      if (next instanceof Error) throw next;
      return next;
    },
    ask: async (choice) => { asked.push(choice); },
    sleep: async (ms) => { clock += ms; },
    now: () => clock,
    phase: (key) => { phases.push(key); },
  };
  return { io, asked, phases, elapsed: () => clock };
}

test("the first open says the demo is being made, then that it is starting, once a new start answers in it", async () => {
  const before = { started: "a1", demoMode: false, demoMade: false };
  const { io, asked, phases, elapsed } = service([before, before, new Error("stopped"), new Error("making"),
    { started: "b2", demoMode: true, demoMade: true }]);
  assert.equal(await switchWorkspace("demo", false, io), "done");
  assert.deepEqual(asked, [{ workspace: "demo", reset: false }]);
  assert.deepEqual(phases, ["demoMaking", "demoStarting"]);
  assert.equal(elapsed(), 4 * SWITCH_POLL_MS, "the old start, still answering, and no answer at all are waited through");
});

test("a reopen and Back to my data say only that they open; Reset says a new demo is being made", async () => {
  const reopen = service([{ started: "a1", demoMode: false, demoMade: true }, { started: "b2", demoMode: true, demoMade: true }]);
  assert.equal(await switchWorkspace("demo", false, reopen.io), "done");
  assert.deepEqual(reopen.phases, ["demoOpening", "demoStarting"]);
  const back = service([{ started: "a1", demoMode: true, demoMade: true }, { started: "b2", demoMode: false, demoMade: true }]);
  assert.equal(await switchWorkspace("own", false, back.io), "done");
  assert.deepEqual(back.phases, ["demoReturning", "demoStarting"]);
  // Reset from inside the demo: the workspace is the same, so only a new start ends the wait.
  const before = { started: "a1", demoMode: true, demoMade: true };
  const reset = service([before, before, before, { started: "c3", demoMode: true, demoMade: true }]);
  assert.equal(await switchWorkspace("demo", true, reset.io), "done");
  assert.deepEqual(reset.asked, [{ workspace: "demo", reset: true }]);
  assert.deepEqual(reset.phases, ["demoResetting", "demoStarting"]);
});

test("a demo that can't be made ends the wait at once: the user's own workspace started again instead", async () => {
  const { io, phases } = service([{ started: "a1", demoMode: false, demoMade: false }, new Error("making"),
    { started: "b2", demoMode: false, demoMade: false, demoFailed: true }]);
  assert.equal(await switchWorkspace("demo", false, io), "demoFailed");
  assert.deepEqual(phases, ["demoMaking"]);
});

test("a switch that never comes back stops waiting after three minutes and says so", async () => {
  const before = { started: "a1", demoMode: true, demoMade: true };
  const { io, elapsed } = service([before, ...Array(SWITCH_WAIT_MS / SWITCH_POLL_MS + 5).fill(new Error("gone"))]);
  assert.equal(await switchWorkspace("own", false, io), "timeout");
  assert.equal(elapsed(), SWITCH_WAIT_MS);
  assert.equal(SWITCH_WAIT_MS, 180000, "the shell's own wait for a first start");
});

test("while it switches, the window says what is happening", () => {
  assert.deepEqual([switchingKey("demo", false, false), switchingKey("demo", false, true), switchingKey("demo", true, true),
    switchingKey("own", false, true)], ["demoMaking", "demoOpening", "demoResetting", "demoReturning"]);
  for (const key of ["settingsDemo", "demoLead", "demoKeptNote", "demoOpenNote", "demoOpen", "demoBack", "demoResetEllipsis",
    "demoReset", "demoResetQuestion", "demoResetBody", "demoOpening", "demoMaking", "demoResetting", "demoReturning",
    "demoStarting", "demoSwitchNote", "demoSwitchFailed", "demoMakeFailed", "demoContinue", "closeAction",
    "demoBannerTitle", "demoBannerUntouched", "statusDemo"]) {
    assert.ok(text.en[key], `en ${key}`);
    assert.ok(text.zh[key], `zh ${key}`);
  }
  assert.equal(text.en.demoLead, "Two months of made-up use, to see every part of DayWright working.");
  assert.deepEqual([text.en.demoBannerTitle, text.en.demoBannerUntouched, text.en.demoBack],
    ["Demo", "your data is untouched", "Back to my data"]);
  assert.deepEqual([text.zh.demoBannerTitle, text.zh.demoBack], ["演示", "回到我的数据"]);
  assert.equal(text.en.saveDemo, undefined, "the old sample-data banner is gone");
});

test("the demo's banner is on every screen, the Guide's too, and goes back to the user's own data", () => {
  assert.match(source("ui/PageBanners.jsx"), /\{day\.demoMode && <DemoBanner \/>\}/);
  assert.match(source("guide/Guide.jsx"), /\{demoMode && <DemoBanner \/>\}/);
  assert.match(source("App.jsx"), /<GuideScreen focus=\{guideFocus\} demoMode=\{Boolean\(day\.demoMode\)\} \/>/);
  for (const path of ["today/TodayScreen.jsx", "calendar/CalendarScreen.jsx", "plans/PlansScreen.jsx", "records/GoalsScreen.jsx",
    "records/TasksScreen.jsx", "records/AreaScreen.jsx", "library/LibraryScreen.jsx"]) {
    assert.match(source(path), /<PageBanners day=\{day\} backendConnected=\{backendConnected\} \/>/, path);
  }
  const banner = source("ui/DemoBanner.jsx");
  assert.match(banner, /useContext\(WorkspaceSwitchContext\)/);
  assert.match(banner, /disabled=\{Boolean\(switching\)\} onClick=\{\(\) => start\("own"\)\}/);
});

test("Settings › Demo opens the demo, goes back, and resets it only once asked again, its buttons off while it switches", () => {
  assert.match(source("settings/SettingsSheet.jsx"), /<DemoSection backendConnected=\{backendConnected\} demoMode=\{demoMode\} \/>/);
  const section = source("settings/DemoSection.jsx");
  assert.match(section, /useContext\(WorkspaceSwitchContext\)/);
  assert.match(section, /start\("demo"\)/);
  assert.match(section, /start\("own"\)/);
  assert.match(section, /onClick=\{\(\) => setAsking\(true\)\}/);
  assert.match(section, /role="alertdialog"[\s\S]{0,400}start\("demo", true\)/, "Reset asks first");
  assert.equal((section.match(/disabled=\{busy\}/g) || []).length, 5, "Open, Back, Reset…, and the confirmation's two");
  const hook = source("settings/useWorkspaceSwitch.js");
  assert.match(hook, /api\("\/api\/workspace", \{ method: "POST", body: JSON\.stringify\(choice\) \}\)/);
  assert.match(hook, /window\.location\.reload\(\)/);
});

test("one switch for the whole window: a full-window state that Escape and clicks don't leave, the app behind it inert", () => {
  const app = source("App.jsx");
  assert.equal((app.match(/useWorkspaceSwitch\(\)/g) || []).length, 1);
  assert.match(app, /<WorkspaceSwitchContext\.Provider value=\{workspaceSwitch\}>/);
  assert.match(app, /<div className="dw-app" inert=\{workspaceSwitch\.active \|\| undefined\}>/);
  assert.match(app, /\{workspaceSwitch\.active && <SwitchOverlay \{\.\.\.workspaceSwitch\} \/>\}/);
  for (const path of ["ui/DemoBanner.jsx", "settings/DemoSection.jsx"]) {
    assert.doesNotMatch(source(path), /useWorkspaceSwitch\(/, `${path} uses the window's one switch`);
  }
  const overlay = source("settings/SwitchOverlay.jsx");
  assert.match(overlay, /role="dialog" aria-modal="true"/);
  assert.match(overlay, /window\.addEventListener\("keydown", hold, true\)/);
  assert.match(overlay, /if \(event\.key === "Escape"\) \{\s*event\.preventDefault\(\);\s*event\.stopImmediatePropagation\(\);/);
  assert.match(overlay, /role="progressbar"/);
  const css = source("bench.css");
  assert.match(css, /\.dw-switch-overlay \{[^}]*position: fixed; inset: 0;/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\) \{[^}]*\.dw-switch-bar span \{ animation: none;/);
});

test("the old demo's own translations are gone; the service's sentences are still put into Chinese", () => {
  const i18n = source("i18n.jsx");
  assert.doesNotMatch(i18n, /demoMessages/);
  assert.match(i18n, /function localizeDemo\(value, language\)/);
  assert.match(i18n, /\(_, task, outcome, plans, minutes, time, step\) => `\$\{task\}在 \$\{plans\} 份已记录计划中/);
});

test("Ava's conversation reads in the demo as it does in the user's own workspace, untranslated", () => {
  assert.doesNotMatch(source("talk/TalkMessage.jsx"), /demoMode/);
  assert.doesNotMatch(source("talk/TalkPanel.jsx"), /demoMode/);
});
