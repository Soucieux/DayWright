import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { guideScreenOf, popoverPlace, screenSection } from "../src/guide/guideCards.js";

const guide = JSON.parse(readFileSync(new URL("../src/guide/guide.json", import.meta.url), "utf8"));
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const VIEW = { width: 1440, height: 900 };
const SIZE = { width: 380, height: 300 };

test("a screen's ? leads to its section of the Guide: the first its cards fall in", () => {
  const wanted = { today: "day", plans: "day", calendar: "day", goals: "work", tasks: "work", areas: "work", learning: "work",
    learningTasks: "work", library: "library", ava: "ava" };
  assert.deepEqual(Object.keys(guide.screens).sort(), Object.keys(wanted).sort());
  for (const [screen, section] of Object.entries(wanted)) assert.equal(screenSection(guide, screen), section, screen);
});

test("each place with a ? names its screen, so the top bar's Guide starts at its section; elsewhere none", () => {
  assert.deepEqual(["today", "plans", "calendar", "goals", "tasks", "library", "learning", "life", "work", "project"].map(guideScreenOf),
    ["today", "plans", "calendar", "goals", "tasks", "library", "learning", "areas", "areas", "areas"]);
  assert.equal(guideScreenOf("guide"), null);
  assert.equal(guideScreenOf("nowhere"), null);
});

test("the popover sits centred under its ?, shifts to stay 8 px inside the window, and flips above when there's no room below", () => {
  const anchor = (left, top) => ({ left, top, right: left + 20, bottom: top + 20 });
  assert.deepEqual(popoverPlace(anchor(500, 100), SIZE, VIEW), { left: 320, top: 128, placement: "below", pointer: 190 });
  assert.deepEqual(popoverPlace(anchor(10, 100), SIZE, VIEW), { left: 8, top: 128, placement: "below", pointer: 16 },
    "at the left edge, its pointer stays on its body");
  assert.deepEqual(popoverPlace(anchor(1410, 100), SIZE, VIEW), { left: 1052, top: 128, placement: "below", pointer: 364 });
  assert.deepEqual(popoverPlace(anchor(500, 820), SIZE, VIEW), { left: 320, top: 512, placement: "above", pointer: 190 });
  assert.deepEqual(popoverPlace(anchor(500, 400), { width: 380, height: 600 }, VIEW), { left: 320, top: 292, placement: "below", pointer: 190 },
    "with room on neither side, it keeps below and inside the window");
});

test("the ? opens its popover and says so; the popover holds the screen's name and ✕, its cards, and Open the full Guide", () => {
  assert.equal(guide.labels.fullGuide, "Open the full Guide");
  assert.equal(guide.labels.close, "Close");
  for (const screen of Object.keys(guide.screens)) assert.ok(guide.screenNames[screen], screen);
  const view = source("guide/Guide.jsx");
  assert.match(view, /aria-haspopup="dialog" aria-expanded=\{open\} aria-controls=\{open \? popoverId : undefined\}/);
  assert.match(view, /onClick=\{\(\) => \(open \? close\(true\) : setOpen\(true\)\)\}/, "pressing the ? again closes it");
  assert.match(view, /\{open && <GuidePopover id=\{popoverId\} screen=\{screen\} anchor=\{buttonRef\} onClose=\{close\} onFullGuide=\{\(\) => \{ close\(false\); onFullGuide\(screen\); \}\} \/>\}/);
  assert.match(view, /return createPortal\(\s*<section id=\{id\} ref=\{boxRef\} className=\{`dw-guide-popover/);
  assert.match(view, /role="dialog" aria-labelledby=\{`\$\{id\}-title`\}/);
  assert.doesNotMatch(view, /aria-modal/, "it isn't modal, so nothing traps focus");
  assert.match(view, /\{guide\.screenNames\[screen\]\}/);
  assert.match(view, /aria-label=\{guide\.labels\.close\} onClick=\{\(\) => onClose\(true\)\}/);
  assert.match(view, /<div className="dw-guide-popover-body"><ScreenGuide screen=\{screen\} \/><\/div>/);
  assert.match(view, /<button type="button" className="dw-link dw-guide-full" onClick=\{onFullGuide\}>\{guide\.labels\.fullGuide\}<\/button>/);
  assert.doesNotMatch(view, /GuideSheet|from "\.\.\/ui\/Sheet"/, "the ? no longer opens a side panel");
});

test("it closes on Escape, ✕ or the ? again, focus going back to the ?; a click elsewhere closes it and leaves focus where it went", () => {
  const view = source("guide/Guide.jsx");
  assert.match(view, /if \(event\.key !== "Escape"\) return;\s*event\.stopPropagation\(\);\s*onClose\(true\);/,
    "Escape closes it alone, never Ava or a side panel too");
  assert.match(view, /document\.addEventListener\("keydown", onKey, true\);/,
    "wherever focus is, as a click on its words leaves it on the page: caught first, before Ava's or a panel's own");
  assert.match(view, /onPointerDown=\{\(event\) => event\.stopPropagation\(\)\}/, "a press in it never reaches what holds its ?");
  assert.match(view, /if \(boxRef\.current\?\.contains\(event\.target\) \|\| anchor\.current\?\.contains\(event\.target\)\) return;\s*onClose\(false\);/);
  assert.match(view, /const close = \(back\) => \{ setOpen\(false\); if \(back\) buttonRef\.current\?\.focus\(\); \};/);
  assert.match(view, /boxRef\.current\?\.querySelector\("\.dw-guide-popover-title"\)\?\.focus\(\)/, "opening moves focus into it");
});

test("Ava's ? opens its popover over her, and a click in it keeps her open; her panel no longer shows the Guide itself", () => {
  const panel = source("talk/TalkPanel.jsx");
  assert.match(panel, /<GuideButton screen="ava" onFullGuide=\{onFullGuide\} \/>/);
  assert.doesNotMatch(panel, /guideShown|dw-talk-guide|ScreenGuide/);
  assert.match(panel, /const inside = \(target\) => Boolean\(panelRef\.current\?\.contains\(target\)\)\s*\|\| \(target instanceof Element && Boolean\(target\.closest\("\.dw-guide-popover"\)\)\);/);
  const css = source("bench.css");
  assert.match(css, /\.dw-guide-popover \{ position: fixed; z-index: 50;/, "above Ava (40), under a centred panel (60)");
  assert.match(css, /\.dw-guide-popover \{[^}]*width: min\(380px, calc\(100vw - 16px\)\); max-height: 60vh;/);
  assert.match(css, /\.dw-guide-popover-body \{[^}]*overflow-y: auto;/, "Ava's five cards scroll inside it");
  assert.match(css, /@media \(max-width: 640px\) \{\s*\.dw-guide-popover \{ inset: 0; width: auto; max-height: none; border-radius: 0; \}/,
    "on a phone it fills the screen");
});

test("Open the full Guide and the top bar's Guide both open the Guide at a screen's section, its heading in view and focused", () => {
  const view = source("guide/Guide.jsx");
  assert.match(view, /<h2 className=\{`dw-guide-section dw-guide-\$\{section\.id\}`\} data-guide-section=\{section\.id\} tabIndex=\{-1\}>/);
  assert.match(view, /focus\.card \? `\[data-guide-card="\$\{focus\.card\}"\]` : `\[data-guide-section="\$\{focus\.section\}"\]`/);
  assert.match(view, /target\?\.scrollIntoView\(\{ block: focus\.card \? "center" : "start" \}\);\s*target\?\.focus\(\{ preventScroll: true \}\);/);
  const app = source("App.jsx");
  assert.match(app, /function openGuideAt\(screen\) \{\s*setConversationOpen\(false\);\s*setGuideFocus\(\{ section: screenSection\(guide, screen\), at: Date\.now\(\) \}\);\s*navigate\("guide"\);/);
  assert.match(app, /const screen = guideScreenOf\(activeTab\);\s*setGuideFocus\(screen \? \{ section: screenSection\(guide, screen\), at: Date\.now\(\) \} : null\);/);
  assert.match(app, /function openGuide\(card\) \{\s*setConversationOpen\(false\);\s*setGuideFocus\(\{ card, at: Date\.now\(\) \}\);/, "See Guide still opens its card");
  assert.doesNotMatch(app, /GuideSheet|guideSheet|openGuideSheet/);
  assert.equal((app.match(/onGuide=\{openGuideAt\}/g) || []).length, 8, "every screen's and the task sheet's ? leads to openGuideAt");
  assert.match(app, /onGuide=\{openGuide\} onFullGuide=\{openGuideAt\}/, "Ava's See Guide keeps opening a card; her ? her section");
});
