import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { FOCUSABLE, nextFocus } from "../src/ui/focusTrap.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("Tab and Shift+Tab move through a centred panel's controls, buttons too, and wrap round at either end", () => {
  assert.equal(nextFocus(4, 1, false), 2);
  assert.equal(nextFocus(4, 3, false), 0, "Tab on the last control goes to the first");
  assert.equal(nextFocus(4, -1, false), 0, "Tab with focus outside goes to the first");
  assert.equal(nextFocus(4, 2, true), 1);
  assert.equal(nextFocus(4, 0, true), 3, "Shift+Tab on the first control goes to the last");
  assert.equal(nextFocus(4, -1, true), 3);
  assert.equal(nextFocus(0, -1, false), null, "a panel with nothing to focus");
  assert.match(FOCUSABLE, /^button:not\(\[disabled\]\):not\(\[tabindex='-1'\]\), input/, "a tab list's other tabs wait");
});

test("each surface is centred or a side panel, as the panel rule sets them", () => {
  // Centred: app-wide, or a short job with one finish; 720 px for Settings and a folder's tree, else 560 px.
  for (const [path, pattern] of [
    ["settings/SettingsSheet.jsx", /<CentredSheet title=\{t\("settingsTitle"\)\} view=\{shown\} wide onClose=\{onClose\}>/],
    ["records/CatchUpSheet.jsx", /<CentredSheet title=\{t\("catchUpTitle"\)\}[^>]*changed=\{count > 0\} onClose=\{onClose\}>/],
    ["records/FromSourceSheet.jsx", /<CentredSheet title=\{t\("fromSourceTitle"\)\}[^>]* wide changed=\{ticked\.size > 0 \|\| Boolean\(address\.trim\(\)\)\}\s+onClose=\{onBack\}>/],
    ["library/FolderSheets.jsx", /<CentredSheet title=\{t\("connectFolderTitle"\)\} wide onClose=\{onClose\}>/],
  ]) assert.match(source(path), pattern, path);
  const folderSheets = source("library/FolderSheets.jsx");
  for (const title of ["updateLocationTitle", "locateTitle", "addWebsiteTitle", "openWithTitle"]) {
    assert.match(folderSheets, new RegExp(`<SheetForm title=\\{t\\("${title}"[\\s\\S]{0,260}? centred onSubmit`), title);
  }
  assert.match(source("library/LibrarySheets.jsx"), /<SheetForm title=\{t\("addToLibraryTitle"\)\}[\s\S]{0,200}? centred onSubmit/);
  assert.doesNotMatch(folderSheets + source("library/LibrarySheets.jsx") + source("settings/SettingsSheet.jsx")
    + source("records/CatchUpSheet.jsx") + source("records/FromSourceSheet.jsx"), /<Sheet /, "no centred surface is still a side sheet");
  // Side: about something on the page; the briefing moves from its floating card into the side panel.
  assert.match(source("records/TaskSheet.jsx"), /<Sheet title=\{t\("taskDetailTitle"\)\} view="detail" hidden=\{hidden\}/);
  assert.match(source("records/GoalsScreen.jsx"), /<SheetForm title=\{goal \? t\("editGoalTitle"\)/);
  assert.doesNotMatch(source("records/GoalsScreen.jsx"), /<SheetForm[^>]* centred/);
  assert.match(source("guide/Guide.jsx"), /<Sheet title=\{guide\.title\} view=\{screen\}/);
  const briefing = source("library/SourceBriefing.jsx");
  assert.match(briefing, /<Sheet title=\{serviceText\(view\.name\)\} returnTo=\{opener\} onClose=\{onClose\}>/);
  assert.doesNotMatch(briefing, /createPortal|position|mousedown/, "no floating card, and no outside click closing it");
});

test("centred panels: dimmed page, focus kept inside, the app behind out of reach, outside clicks only without changes", () => {
  const centred = source("ui/CentredSheet.jsx");
  assert.match(centred, /className="dw-centred-scrim" onMouseDown=\{onScrim\}/);
  assert.match(centred, /role="dialog" aria-modal="true"/);
  assert.match(centred, /event\.preventDefault\(\);\s*if \(!unsaved\) onClose\(\);/, "focus stays in it after a press beside it");
  assert.match(centred, /onInput=\{\(\) => setEdited\(true\)\} onChange=\{\(\) => setEdited\(true\)\}/);
  assert.match(centred, /const next = nextFocus\(controls\.length, controls\.indexOf\(document\.activeElement\), event\.shiftKey\);/);
  // Leaving for a side panel: straight away without changes, else only once the user says Leave.
  assert.match(centred, /leave\(then\) \{\s*if \(unsaved\) setLeaving\(\(\) => then\);\s*else closeThen\(then\);/);
  assert.match(centred, /onClick=\{\(\) => closeThen\(leaving\)\}>\{t\("leaveAction"\)\}/);
  assert.match(centred, /function closeThen\(then\) \{\s*onClose\(\);\s*window\.setTimeout\(then\);/, "the side panel opens once the app is in reach");
  assert.match(source("library/SourceBriefing.jsx"), /if \(centred\) centred\.leave\(open\);\s*else open\(\);/);
  // The app behind is inert while any centred panel is open; Ava's shortcut waits too.
  const app = source("App.jsx");
  assert.match(app, /const centredOpen = useCentredOpen\(\);/);
  assert.match(app, /event\.key\.toLowerCase\(\) === "k" && !centredOpen/);
  // Side panels never trap focus: the page stays in reach.
  assert.doesNotMatch(source("ui/Sheet.jsx"), /aria-modal|nextFocus|inert/);
  const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
  assert.match(css, /\.dw-centred \{[^}]*width: min\(560px, 100%\); max-height: 85vh;/);
  assert.match(css, /\.dw-centred-wide \{ width: min\(720px, 100%\); \}/);
  assert.match(css, /@media \(max-width: 640px\) \{[^}]*\}\s*\.dw-centred-scrim \{ display: block; padding: 0; \}\s*\.dw-centred, \.dw-centred-wide \{ width: 100%; height: 100%; max-height: none;/,
    "on a phone a centred panel fills the screen");
});

test("a side panel's first focus skips disabled controls and lands on the first usable one, as a centred panel's does", () => {
  const sheet = source("ui/Sheet.jsx");
  assert.match(sheet, /import \{ FOCUSABLE \} from "\.\/focusTrap";/);
  assert.match(sheet, /const first = sheet\?\.querySelector\("\.dw-sheet-body"\)\?\.querySelector\(FOCUSABLE\);\s*\(first \|\| sheet\?\.querySelector\(FOCUSABLE\)\)\?\.focus\(\);/);
  assert.match(sheet, /document\.querySelector\("\.dw-sheet:not\(\[hidden\]\)"\)\?\.querySelector\(FOCUSABLE\)/, "and on its way back");
  assert.doesNotMatch(sheet, /\.dw-sheet-body button|:not\(\[hidden\]\) button/, "never a plain button, which may be disabled");
});

test("a centred panel opens over a side one, which waits beneath; a side one replaces the Guide's and the briefing", () => {
  const app = source("App.jsx");
  const opener = (name) => app.match(new RegExp(`function ${name}\\([^)]*\\) \\{([\\s\\S]*?)\\n  \\}`))[1];
  for (const name of ["openCatchUp", "openSettingsSheet", "addToLibrary"]) {
    assert.doesNotMatch(opener(name), /setSheet\(null\)|setGuideSheet\(null\)|setBriefing\(null\)/, `${name} keeps the side panel`);
  }
  assert.match(opener("openSheet"), /setGuideSheet\(null\);\s*setBriefing\(null\);/);
  assert.match(app, /const sheetOpen = sheetRow !== undefined \|\| guideSheet !== null \|\| briefing !== null;/);
  // From a source opens centred over the New task form, which keeps what was typed.
  assert.match(source("records/TaskSheet.jsx"),
    /<\/Sheet>\s*\{fromSource && <FromSourceSheet date=\{fromSource\}[^>]*onBack=\{\(\) => setFromSource\(null\)\} onClose=\{onClose\} \/>\}/);
  // One briefing at a time: another item's swaps in, and a task's or goal's panel waits beneath it.
  assert.match(app, /setBriefing\(\{ id: source\.id, source, opener \}\);/);
  assert.match(app, /<SourceBriefing key=\{briefing\.id\}/);
  assert.match(app, /hidden=\{briefing !== null\}/);
});

test("Settings: three tabs, Models first, opened on the tab asked for; Ava's memory cards link to Memory", () => {
  const settings = source("settings/SettingsSheet.jsx");
  assert.match(settings, /const TABS = \[\["models", "settingsModels"\], \["memory", "settingsMemory"\], \["demo", "settingsDemo"\]\];/);
  assert.match(settings, /export function SettingsSheet\(\{ tab = "models",/);
  assert.match(settings, /role="tablist"/);
  assert.match(settings, /\{shown === "memory" && <MemorySection/);
  assert.match(source("settings/models.js"), /new CustomEvent\(SETTINGS_EVENT, \{ detail: \{ tab \} \}\)/);
  assert.match(source("App.jsx"), /setSettings\(\{ tab: event\?\.detail\?\.tab \|\| "models", at: Date\.now\(\) \}\);/);
  const card = source("talk/ProposalCard.jsx");
  assert.match(card, /onClick=\{\(\) => openSettings\("memory"\)\}>\{t\("settingsMemoryPlace"\)\}/);
  assert.equal((card.match(/\["lock", <MemorySettingsLine key="memory" \/>\]/g) || []).length, 2, "the remember card and the change card");
  for (const language of ["en", "zh"]) {
    assert.equal(text[language].proposalRememberSettings.split("{place}").length, 2, `${language}: one place for the link`);
    for (const key of ["settingsMemoryPlace", "leaveUnsavedQuestion", "leaveAction", "stayAction"]) assert.ok(text[language][key], `${language} ${key}`);
  }
  assert.equal(text.en.settingsMemoryPlace, "Settings › Memory");
  assert.equal(text.zh.settingsMemoryPlace, "设置 › 记忆");
});

test("the Guide's button is outlined like Ava's, with its own book, and filled while the Guide is on show", () => {
  assert.match(source("shell/Shell.jsx"), /aria-current=\{current \? "page" : undefined\} onClick=\{onGuide\}>\s*<Icon name="guide" size=\{18\} \/>\{guide\.title\}/);
  const css = readFileSync(new URL("../src/bench.css", import.meta.url), "utf8");
  assert.match(css, /\.dw-guide-link \{[^}]*height: 36px;[^}]*border: 1px solid var\(--dw-line-2\); border-radius: var\(--dw-radius-control\); background: var\(--dw-surface\);/);
  assert.match(css, /\.dw-guide-link\[aria-current="page"\] \{ border-color: var\(--dw-ink\); background: var\(--dw-ink\); color: var\(--dw-surface\); \}/);
  assert.ok(readFileSync(new URL("../design/icons/guide.svg", import.meta.url), "utf8").includes('stroke-width="1.75"'));
});
