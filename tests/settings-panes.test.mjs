import assert from "node:assert/strict";
import test from "node:test";
import { PANES, PATH_CHARACTERS, demoState, middleCut, modelPill, runnerPill } from "../src/settings/panes.js";
import { tabAfter } from "../src/ui/tabs.js";
import { cssRule as rule, interfaceText, say, source } from "./interfaceText.mjs";

const text = interfaceText();
const en = say("en");
const zh = say("zh");
const css = source("bench.css");

test("Settings' header is a Mac toolbar of panes: Models, Memory, Schedule and Demo, each an icon above its name", () => {
  assert.deepEqual(PANES, [["models", "settingsModels", "chip"], ["memory", "settingsMemory", "brain"],
    ["schedule", "settingsSchedule", "calendar"], ["demo", "settingsDemo", "laptop"]]);
  for (const [, , icon] of PANES) {
    assert.ok(source(`../design/icons/${icon}.svg`).includes('stroke-width="1.75"'), icon);
  }
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /<CentredSheet title=\{t\(paneKey\)\} name=\{t\("settingsTitle"\)\} wide toolbar=\{toolbar\} onClose=\{onClose\}>/,
    "the chosen pane's name is the visible title; the dialog's name stays Settings; a pane chosen keeps focus on its tab, "
    + "as no view moves it into the pane");
  assert.match(sheet, /<TabList label=\{t\("settingsTitle"\)\} idBase="dw-settings" className="dw-panes" tabClassName="dw-pane" selected=\{shown\}\s+onSelect=\{setShown\}/,
    "the panes are the one tab list every page uses, with the toolbar's look");
  assert.match(sheet, /<Icon name=\{icon\} size=\{22\} \/><span>\{t\(key\)\}<\/span>/);
  assert.match(sheet, /role="tabpanel" aria-labelledby=\{`dw-settings-tab-\$\{shown\}`\}/, "each pane is labelled by its tab");
  const centred = source("ui/CentredSheet.jsx");
  assert.match(centred, /aria-labelledby=\{name \? undefined : titleId\} aria-label=\{name\}/);
  assert.match(centred, /\{toolbar && <div className="dw-sheet-toolbar">\{toolbar\}<\/div>\}/);
});

test("the arrow keys, Home and End move to a pane and choose it", () => {
  const panes = PANES.map(([id]) => id);
  assert.equal(tabAfter(panes, "models", "ArrowRight"), "memory");
  assert.equal(tabAfter(panes, "demo", "ArrowRight"), "models", "wrapping round");
  assert.equal(tabAfter(panes, "models", "ArrowLeft"), "demo");
  assert.equal(tabAfter(panes, "memory", "Home"), "models");
  assert.equal(tabAfter(panes, "models", "End"), "demo");
  assert.equal(tabAfter(panes, "models", "Enter"), null);
});

test("the chosen pane is tinted, the others quiet; no item has a border, shadow or shared track", () => {
  assert.match(rule(".dw-sheet-toolbar-head"), /background: var\(--dw-sunken\);/);
  assert.match(rule(".dw-sheet-toolbar-head"), /border-bottom: 1px solid var\(--dw-line\);/);
  assert.match(rule(".dw-pane"), /width: 84px;/);
  assert.match(rule(".dw-pane"), /gap: 6px;/);
  assert.match(rule(".dw-pane"), /border: 0;/);
  assert.match(rule(".dw-pane"), /background: transparent;/);
  assert.match(rule(".dw-pane"), /color: var\(--dw-text-2\);/);
  assert.match(rule(".dw-pane"), /font-size: 12px;/);
  assert.match(rule('.dw-pane[aria-selected="true"]'), /background: var\(--dw-ground-2\); color: var\(--dw-ink\);/);
  assert.match(rule(".dw-pane:hover"), /background: var\(--dw-ground\);/);
  assert.match(rule(".dw-pane:focus-visible"), /outline: 2px solid var\(--dw-focus\);/);
  assert.match(rule(".dw-pane"), /border-radius: 8px;/);
  assert.doesNotMatch(rule(".dw-panes") + rule(".dw-pane"), /box-shadow|border: 1px/);
  assert.match(css, /@media \(max-width: 640px\) \{[^@]*\.dw-pane \{ flex: 1; width: auto; \}/, "on a phone the panes share the width");
});

test("each model's state is a pill: Ready, Checking…, Missing or Doesn't match; the runner Found or Not found", () => {
  assert.deepEqual(modelPill("ready"), { tone: "success", icon: "check", label: "pillReady" });
  assert.deepEqual(modelPill("checking"), { tone: "neutral", icon: "clock", label: "pillChecking" });
  for (const state of ["missing", "noFolder", "folderNotFound"]) {
    assert.deepEqual(modelPill(state), { tone: "warning", icon: "alert", label: "pillMissing" }, state);
  }
  assert.deepEqual(modelPill("mismatch"), { tone: "danger", icon: "x", label: "pillMismatch" });
  assert.deepEqual(runnerPill("found"), { tone: "success", icon: "check", label: "pillFound" });
  assert.deepEqual(runnerPill("notFound"), { tone: "warning", icon: "alert", label: "pillNotFound" });
  assert.deepEqual(runnerPill("none"), { tone: "neutral", icon: "alert", label: "pillNotChosen" });
  assert.deepEqual(["pillReady", "pillChecking", "pillMissing", "pillMismatch", "pillFound", "pillNotFound", "pillCantFind"].map((key) => en(key)),
    ["Ready", "Checking…", "Missing", "Doesn't match", "Found", "Not found", "Can't be found"]);
  for (const tone of ["success", "neutral", "warning", "danger"]) assert.match(css, new RegExp(`\\.dw-status-pill\\.is-${tone} \\{`), tone);
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /<StatusPill \{\.\.\.modelPill\(model\.state\)\} \/>/);
  assert.match(sheet, /model\.state === "ready" \|\| model\.state === "checking" \? model\.name : modelStateText\(model, models, t\)/,
    "a model not ready names the exact place looked in");
  assert.deepEqual([en("modelRoleChat"), en("modelRoleEmbedding"), en("modelRoleSpeech")], ["Chat · Ava and plans", "Search · Library", "Voice"]);
});

test("the folder's path is cut in its middle, whole on hover or focus", () => {
  const path = "/Users/someone/Documents/A very long folder name/Shared models/AI-Models";
  const cut = middleCut(path);
  assert.equal(cut.length, PATH_CHARACTERS);
  assert.ok(cut.startsWith("/Users/someone") && cut.endsWith("AI-Models") && cut.includes("…"), cut);
  assert.equal(middleCut("/Users/me/AI-Models"), "/Users/me/AI-Models");
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /<span className="dw-set-path" tabIndex=\{0\} title=\{models\.folder\}>/);
  assert.match(sheet, /<span className="dw-set-path-cut" aria-hidden="true">\{middleCut\(models\.folder\)\}<\/span>/);
  assert.match(css, /\.dw-set-path:hover \.dw-set-path-cut, \.dw-set-path:focus \.dw-set-path-cut \{ display: none; \}/);
});

test("the folder row: Change… and a ⋯ menu of Type a path… and Stop using this folder, or Choose folder… with none", () => {
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /<ActionMenu icon="more" label=\{t\("modelsMore"\)\} items=\{\[\s*\{ value: "type", label: t\("modelsTypePath"\) \},\s*\.\.\.\(models\.folder \? \[\{ value: "stop", label: t\("modelsStopUsing"\), note: t\("modelsStopNote"\) \}\] : \[\]\),\s*\]\}/);
  assert.match(sheet, /models\.state === "none" \?[\s\S]{0,200}dw-button dw-button-primary[\s\S]{0,120}t\("modelsChooseFolder"\)/);
  assert.match(sheet, /<StatusPill tone="warning" icon="alert" text=\{t\("pillCantFind"\)\} \/>/);
  assert.match(sheet, /const typedPath = typing && \(\s*<form className="dw-field dw-settings-typed"/, "Type a path… reveals the field");
  assert.match(sheet, /\{typing === "folder" && typedPath\}/, "under the folder's row, with Use this folder");
  assert.match(source("ui/ActionMenu.jsx"), /\{item\.note && <span className="dw-menu-note">\{item\.note\}<\/span>\}/);
  assert.deepEqual([en("modelsChange"), en("modelsTypePath"), zh("modelsTypePath")], ["Change…", "Type a path…", "输入路径…"]);
  assert.match(sheet, /<div className="dw-set-head"><h3 className="dw-set-heading">\{t\("settingsModels"\)\}<\/h3>/, "the list's header line reads Models");
});

test("the runner row: Choose runner… with none, else Change…, and a ⋯ menu of Type a path… and Stop using this runner", () => {
  const sheet = source("settings/SettingsSheet.jsx");
  assert.match(sheet, /<ActionMenu icon="more" label=\{t\("runnerMore"\)\} items=\{\[\s*\{ value: "type", label: t\("modelsTypePath"\) \},\s*\.\.\.\(models\.runner\.location \? \[\{ value: "stop", label: t\("runnerStopUsing"\), note: t\("runnerStopNote"\) \}\] : \[\]\),\s*\]\}/);
  assert.match(sheet, /t\(models\.runner\.state === "none" \? "runnerChoose" : "modelsChange"\)/);
  assert.match(sheet, /api\("\/api\/models\/runner\/choose", \{ method: "POST" \}\)/);
  assert.match(sheet, /api\("\/api\/models\/runner", \{ method: "DELETE" \}\)/);
  assert.match(sheet, /\{typing === "runner" && typedPath\}/, "a typed path for the runner, under its row");
  assert.deepEqual([en("runnerChoose"), en("runnerStopUsing"), en("pillNotChosen"), zh("runnerStopUsing")],
    ["Choose runner…", "Stop using this runner", "Not chosen", "停止使用此运行程序"]);
});

test("Memory: rules and notes as tagged rows with Edit and Delete icons; the past ones under a disclosure", () => {
  const section = source("settings/MemorySection.jsx");
  assert.match(section, /const kindTag = \(entry\) => <span className="dw-set-tag">\{entry\.kind === "rule" \? t\(RULE_KINDS\[entry\.ruleKind\]\) : areaName\(entry\.area, t\)\}<\/span>;/);
  assert.match(section, /tag=\{kindTag\(rule\)\}/);
  assert.match(section, /tag=\{kindTag\(note\)\}/);
  assert.match(section, /`\$\{ruleWhat\(rule, t\)\} · \$\{daysText\(rule\.days, t, language\)\}`/);
  assert.match(section, /aria-label=\{t\("memoryEditNamed", \{ line \}\)\}/);
  assert.match(section, /aria-label=\{t\("memoryDeleteNamed", \{ line \}\)\}/);
  assert.match(section, /className="dw-set-disclosure" aria-expanded=\{pastOpen\}/);
  assert.equal(en("memoryPastToggle", { count: 2 }), "Past · 2 ended");
  assert.match(section, /editable=\{false\}/, "a past entry can only be deleted");
  assert.match(section, /stepTwoOfTwo/, "Delete takes two steps");
  assert.match(section, /memoryEmpty/, "the empty state line stays");
});

test("Demo: one card, its state line and one way in or back, with a quiet Reset…", () => {
  assert.deepEqual(demoState(false, null), { key: "demoStateNotMade", values: {} });
  assert.deepEqual(demoState(false, "2026-10-12"), { key: "demoStateMade", values: { date: "2026-10-12" } });
  assert.deepEqual(demoState(true, "2026-10-12"), { key: "demoStateOpen", values: {} });
  assert.deepEqual([en("demoStateNotMade"), en("demoStateMade", { date: "12 Oct" }), en("demoStateOpen")],
    ["Not made yet", "Made 12 Oct · kept until you reset it", "Open now"]);
  const demo = source("settings/DemoSection.jsx");
  assert.match(demo, /<div className="dw-set-card">\s*<span className="dw-set-card-icon"><Icon name="laptop" size=\{22\} \/><\/span>/);
  assert.match(demo, /t\("demoCardTitle"\)/);
  assert.match(demo, /api\("\/api\/health"\)/);
  assert.equal(en("demoCardTitle"), "Demo workspace");
});

test("every pane opens with one short line, and says so in one line while the service is away", () => {
  const sheet = source("settings/SettingsSheet.jsx");
  assert.doesNotMatch(sheet + source("settings/MemorySection.jsx") + source("settings/DemoSection.jsx"), /dw-section-label/,
    "no pane repeats its name");
  for (const key of ["modelsLead", "memoryLead", "demoLead"]) {
    for (const language of ["en", "zh"]) assert.ok(text[language][key].length <= (language === "en" ? 120 : 60), `${language} ${key}`);
  }
  for (const path of ["settings/SettingsSheet.jsx", "settings/MemorySection.jsx", "settings/DemoSection.jsx"]) {
    assert.match(source(path), /<p className="dw-set-lead">\{t\("settingsServiceOff"\)\}<\/p>/, path);
  }
});
