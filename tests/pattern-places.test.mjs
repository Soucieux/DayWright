import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { paceRow, stateNote } from "../src/patterns/patternText.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const say = (language) => (key, values = {}) => {
  assert.ok(text[language][key], `${language} ${key}`);
  return text[language][key].replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match);
};
const en = say("en");
const zh = say("zh");
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const NB = " ";

test("every area page lists its repeating tasks' planned against actual, and only the Learn page its section pace", () => {
  const screen = source("records/AreaScreen.jsx");
  assert.match(screen, /<RepeatingCard key="repeating" domain=\{domain\} data=\{data\} \/>/);
  assert.equal((screen.match(/<PaceCard /g) || []).length, 1, "on the Learn page alone");
  assert.match(screen, /learning: \[[^\]]*<PaceCard key="pace" data=\{data\} \/>/);
  const parts = source("patterns/AreaPatterns.jsx");
  assert.match(parts, /<PairList rows=\{repeating\.rows\} label=\{t\("patternsPairsTasksLabel"\)\} byTask \/>/);
  assert.match(parts, /pairsLead\(repeating\.finding, t, language, true\)/);
  assert.match(parts, /t\("patternPairsTasksCaption", \{ area: t\(domain\) \}\)/);
});

test("a repeating task's list needs three fully done times, and a source's pace two sections", () => {
  assert.equal(stateNote("repeating", { state: "few", count: 2, threshold: 3, unit: "tasks", basis: 0 }, "all", en).text,
    "Planned against actual appears after 3 fully done times of one repeating task. 2 so far.");
  assert.equal(stateNote("pace", { state: "few", count: 1, threshold: 2, unit: "sections", basis: 1 }, "all", en).text,
    "Section pace appears after 2 sections ticked in timed tasks. 1 so far.");
  assert.deepEqual(paceRow({ sourceId: "b", title: "Directives", minutes: 8, sections: 3 }, en, "en"),
    { label: "Directives: about 8 min a section, 3 sections", value: `8${NB}min`, sections: "3 sections" });
  assert.equal(paceRow({ sourceId: "b", title: "Directives", minutes: 8, sections: 3 }, zh, "zh").sections, "3 个章节");
});

test("Life's Energy card adds one line on how energy changes how long tasks take, and a learning task its pace", () => {
  const energy = source("records/AreaCards.jsx");
  assert.match(energy, /<EnergyLine finding=\{data\.patterns\?\.energy\} \/>/);
  const line = source("patterns/AreaPatterns.jsx");
  assert.match(line, /energyLead\(finding, t, true\)/);
  assert.match(line, /\["longer", "shorter", "hardly"\]\.includes\(finding\?\.kind\)/, "never says nothing on the Energy card itself");
  const checklist = source("records/Checklist.jsx");
  assert.match(checklist, /taskPaceLine\(learned\.pace, progress, minutes, t, language\)/);
  assert.match(checklist, /minutes=\{task\.duration_minutes\}/);
  assert.match(source("bench.css"), /\.dw-pace-line \{[^}]*text-align: start/);
});
