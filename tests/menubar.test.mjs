import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { PANEL_VIEW, isPanelView, shellAddress, taskFacts } from "../src/menubar/panel.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const say = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (_, name) => values[name]);

test("the panel is the view the desktop session opens for the menu bar, and the window shows it instead of the workbench", () => {
  assert.equal(PANEL_VIEW, "menubar");
  assert.equal(isPanelView("?view=menubar"), true);
  assert.equal(isPanelView("?view=other"), false);
  assert.equal(isPanelView(""), false);
  assert.match(readFileSync(new URL("../backend/app/desktop.py", import.meta.url), "utf8"), /PANEL_VIEW = "menubar"/);
  assert.match(source("App.jsx"), /isPanelView\(window\.location\.search\) \? <MenuBarPanel \/> : <DayWrightApp \/>/);
});

test("the panel asks the shell only through daywright:// addresses, which the shell answers", () => {
  assert.equal(shellAddress("open"), "daywright://open");
  assert.equal(shellAddress("refresh"), "daywright://refresh");
  const shell = readFileSync(new URL("../src-tauri/src/menubar.rs", import.meta.url), "utf8");
  assert.match(shell, /const SHELL_SCHEME: &str = "daywright";/);
  assert.match(shell, /Some\("open"\) =>/);
  assert.match(shell, /Some\("refresh"\) =>/);
});

test("each task says its time taken, or when it starts, and its set time and whose it is", () => {
  const current = { title: "Review", start: "14:00", minutes: 60, durationSource: "user" };
  assert.deepEqual(taskFacts(current, 32, say("en"), "en"), ["32 min taken", "1 h, you set"]);
  const next = { title: "Read", start: null, minutes: 45, durationSource: "estimate" };
  assert.deepEqual(taskFacts(next, null, say("en"), "en"), ["Untimed", "45 min, estimated"]);
  assert.deepEqual(taskFacts({ ...next, start: "15:30" }, null, say("en"), "en"), ["15:30", "45 min, estimated"]);
  assert.deepEqual(taskFacts(next, null, say("zh"), "zh"), ["未定时", "45 分钟，估计"]);
});

test("the panel shows the current and the next task, each with its own status control, and opens DayWright", () => {
  const panel = source("menubar/MenuBarPanel.jsx");
  assert.equal((panel.match(/<PanelTask /g) || []).length, 2);
  assert.match(panel, /<StatusControl variant="segmented"/);
  assert.match(panel, /askShell\("open"\)/);
  assert.match(panel, /askShell\("refresh"\)/);
  assert.match(panel, /`\/api\/daily-items\/\$\{task\.id\}\/status`/);
  assert.match(panel, /MINUTE_MS - \(Date\.now\(\) % MINUTE_MS\)/, "renews at each minute's turn");
  assert.match(panel, /addEventListener\("focus", load\)/, "and whenever it is shown");
});

test("the workbench tells the service its language, for the menu bar's title, and reloads when its window returns", () => {
  assert.match(source("App.jsx"), /api\("\/api\/interface-language", \{ method: "PUT", body: JSON\.stringify\(\{ language \}\) \}\)/);
  assert.match(source("workspace.js"), /addEventListener\("visibilitychange", reload\)/);
});
