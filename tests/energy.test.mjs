import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { noticeText } from "../src/talk/notices.js";
import { proposalView } from "../src/talk/proposal.js";
import { ENERGY_HIGH, ENERGY_LOW, energyBars, energyMeter, energySteps, latestReading, periodDays } from "../src/ui/visuals.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const guide = JSON.parse(readFileSync(new URL("../src/guide/guide.json", import.meta.url), "utf8"));
/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);
const card = (id) => guide.sections.flatMap((section) => section.cards).find((item) => item.id === id);

test("low and high are the service's: 2 or below, and 4 or above", () => {
  const service = readFileSync(new URL("../backend/app/task_review.py", import.meta.url), "utf8");
  assert.deepEqual([ENERGY_LOW, ENERGY_HIGH], [Number(service.match(/^LOW_ENERGY = (\d)/m)[1]), Number(service.match(/^HIGH_ENERGY = (\d)/m)[1])]);
});

test("a day's readings are steps, placed by time from 09:00 to 22:00 and by level from 1 to 5", () => {
  const steps = energySteps([{ level: 2, time: "07:30" }, { level: 4, time: "15:30" }, { level: 3, time: "23:10" }], "22:00");
  assert.deepEqual(steps.map(({ left, width, bottom, low, rise }) => ({ left, width, bottom, low, rise })), [
    { left: 0, width: 50, bottom: 25, low: true, rise: null },
    { left: 50, width: 50, bottom: 75, low: false, rise: { bottom: 25, height: 50 } },
    { left: 100, width: 0, bottom: 50, low: false, rise: { bottom: 50, height: 25 } },
  ]);
  assert.deepEqual(energySteps([{ level: 5, time: "09:00" }], "12:15").map((step) => [step.left, step.width]), [[0, 25]],
    "today's last reading holds until now");
});

test("each day's average is a bar out of 5, with a thin line from its lowest to its highest reading", () => {
  assert.deepEqual(energyBars([{ date: "2026-10-01", average: 3, low: 1, high: 5 }, { date: "2026-10-02", average: 2, low: 2, high: 2 },
    { date: "2026-10-03", average: null, low: null, high: null }]).map(({ height, rangeBottom, rangeHeight, low, empty }) =>
    ({ height, rangeBottom, rangeHeight, low, empty })), [
    { height: 60, rangeBottom: 20, rangeHeight: 80, low: false, empty: false },
    { height: 40, rangeBottom: 40, rangeHeight: 0, low: true, empty: false },
    { height: 0, rangeBottom: 0, rangeHeight: 0, low: false, empty: true },
  ]);
});

test("a week or month lays out every one of its days, reported or not", () => {
  const days = periodDays("2026-09-28", "2026-10-04", [{ date: "2026-09-30", average: 2.5, low: 2, high: 3 }]);
  assert.equal(days.length, 7);
  assert.deepEqual([days[0], days[2]], [{ date: "2026-09-28", average: null, low: null, high: null },
    { date: "2026-09-30", average: 2.5, low: 2, high: 3 }]);
  assert.equal(periodDays("2026-02-01", "2026-02-28", []).length, 28);
});

test("the Calendar meter fills as many of its 5 steps as the average rounds to, in caution at 2 or below, none without a reading", () => {
  assert.deepEqual(energyMeter(2.5), { steps: [true, true, true, false, false], caution: false, empty: false });
  assert.deepEqual(energyMeter(2), { steps: [true, true, false, false, false], caution: true, empty: false });
  assert.deepEqual(energyMeter(4.4).steps.filter(Boolean).length, 4);
  assert.deepEqual(energyMeter(null), { steps: [false, false, false, false, false], caution: false, empty: true });
});

test("each month cell has the meter under its marks, no visible text, and its level in the cell's name", () => {
  const calendar = source("calendar/CalendarScreen.jsx");
  const cell = calendar.slice(calendar.indexOf("function DayCell("), calendar.indexOf("\n}\n", calendar.indexOf("function DayCell(")));
  assert.match(cell, /record\?\.energy != null && t\("cellEnergy", \{ level: record\.energy \}\)/);
  assert.ok(cell.indexOf("<EnergyMeter average={record.energy} />") > cell.indexOf('className="dw-cal-dots"'), "after the marks and dots");
  assert.match(cell, /\{record\?\.energy != null && <EnergyMeter average=\{record\.energy\} \/>\}/, "absent without a reading");
  const visuals = source("ui/AreaVisuals.jsx");
  const meter = visuals.slice(visuals.indexOf("export function EnergyMeter("), visuals.indexOf("\n}\n", visuals.indexOf("export function EnergyMeter(")));
  assert.match(meter, /aria-hidden=\{label \? undefined : "true"\}/, "a meter without a name is hidden, as the cell names it");
  assert.match(meter, /dw-energy-meter-caution/);
  assert.doesNotMatch(meter.slice(meter.indexOf("return (")), /\{t\(|>\{(average|label)\}</, "no visible text in the meter");
  assert.match(source("bench.css"), /\.dw-energy-meter-caution \.dw-meter-on \{[^}]*var\(--dw-caution-/);
});

test("the day panel shows the meter larger, outlined and empty without a reading, named for its level", () => {
  assert.match(source("calendar/DayPanel.jsx"),
    /<EnergyMeter average=\{day\.energy\} large label=\{day\.energy == null \? t\("dayEnergyNone"\) : t\("dayEnergy", \{ level: day\.energy \}\)\} \/>/);
  const css = source("bench.css");
  assert.match(css, /\.dw-energy-meter-large \{/);
  assert.match(css, /\.dw-energy-meter-empty \.dw-meter-step \{[^}]*border: 1px dashed/);
});

test("Today's row shows the latest reading, and tapping the level already shown adds nothing", () => {
  assert.equal(latestReading([{ level: 2, time: "09:00" }, { level: 4, time: "12:00" }]), 4);
  assert.equal(latestReading([]), null);
  assert.match(source("today/TodayScreen.jsx"), /<EnergyRow level=\{latestReading\(day\.energyReadings\)\}/);
  assert.match(source("workspace.js"), /if \(!backendConnected \|\| level === latestReading\(day\.energyReadings\)\) return;/);
});

test("Ava's energy card says the reading and today's average before and after", () => {
  assert.deepEqual(proposalView({ actionType: "set_energy", payload: { date: "2026-10-05", level: 4, before: 3, after: 3.5 } }, []),
    { kind: "energy", date: "2026-10-05", level: 4, before: 3, after: 3.5 });
  const cardView = source("talk/ProposalCard.jsx");
  for (const key of ["proposalEnergyTitle", "proposalEnergyReading", "proposalEnergyAverage", "proposalEnergyAverageNew", "proposalEnergyToday"]) {
    assert.match(cardView, new RegExp(`t\\("${key}"`), key);
  }
  assert.match(source("workspace.js"), /set_energy: "noticeEnergySaved"/);
});

test("each area's note on the day's energy is worded with its numbers", () => {
  const note = (kind, values) => noticeText({ kind, values }, t, "en");
  assert.equal(note("energy-short-review", { energy: 2, taskTitle: "Spanish lesson" }), 'energyNoteShortReview {"energy":2,"title":"Spanish lesson"}');
  assert.equal(note("energy-harder-session", { energy: 4.5, taskTitle: "Spanish lesson" }), 'energyNoteHarderSession {"energy":4.5,"title":"Spanish lesson"}');
  assert.equal(note("energy-heavy-load", { energy: 2, minutes: 210 }), 'energyNoteHeavyLoad {"energy":2,"minutes":"3 h 30 min"}');
  assert.equal(note("energy-biggest-work", { energy: 4, taskTitle: "Quarterly report", minutes: 120 }),
    'energyNoteBiggestWork {"energy":4,"title":"Quarterly report","minutes":"2 h"}');
  assert.equal(note("energy-small-step", { energy: 1.5, taskTitle: "Pick tiles" }), 'energyNoteSmallStep {"energy":1.5,"title":"Pick tiles"}');
  assert.equal(note("energy-next-big-step", { energy: 4, taskTitle: "Pick tiles" }), 'energyNoteNextBigStep {"energy":4,"title":"Pick tiles"}');
});

test("Life's Energy card shows the day's steps and each day's average with its range", () => {
  const cards = source("records/AreaCards.jsx");
  const energy = cards.slice(cards.indexOf("export function EnergyCard("), cards.indexOf("\n}\n", cards.indexOf("export function EnergyCard(")));
  assert.match(energy, /<EnergySteps readings=\{data\.energyReadings\}/);
  assert.match(energy, /<EnergyBars days=\{data\.energyWeek\}/);
  const visuals = source("ui/AreaVisuals.jsx");
  assert.match(visuals, /\{bar\.rangeHeight > 0 && <span className="dw-energy-range"/, "a day of one reading, or of equal ones, draws no range line");
});

test("Summary's report shows the day's steps, a bar per day for a week or month, and its figures, comparing only with enough days", () => {
  const reports = source("calendar/SummaryReports.jsx");
  const block = reports.slice(reports.indexOf("function EnergyReport("), reports.indexOf("\n}\n", reports.indexOf("function EnergyReport(")));
  assert.match(block, /kind === "day" && <EnergySteps/);
  assert.match(block, /\(kind === "week" \|\| kind === "month"\) && <EnergyBars days=\{periodDays\(energy\.start, energy\.end, energy\.days\)\}/);
  assert.match(block, /energy\.comparison \?/);
  assert.match(block, /const share = \(rate\) => \(rate == null \? "–" : `\$\{rate\}%`\);/, "a share with no tasks reads –, not –%");
  for (const language of ["en", "zh"]) {
    for (const key of ["energyCompareLow", "energyCompareOther", "energyCompareArea"]) {
      assert.doesNotMatch(text[language][key], /\}%/, `${language} ${key} leaves the % to the share`);
    }
  }
  assert.match(reports, /report\.energy \? <EnergyReport/, "a report saved before v4.3, with no energy figures, still shows");
});

test("the Guide's Energy, Repeats and Agents cards say what they now do", () => {
  assert.deepEqual([card("energy").for, card("energy").do, card("energy").rule], [
    "matching the day to you.", "tap 1–5 at the top of Today, or tell Ava; change it any time today.",
    "the day's average counts; 2 or below suggests Lighter day, 4 or above Deep focus."]);
  assert.equal(card("repeats").rule, "a change made from a past day applies from today on, or tomorrow if today's is already reported or planned.");
  assert.equal(card("agents").rule, "the Orchestrator proposes; agents estimate only lengths you didn't set, never from skipped or unanswered tasks.");
});

test("every new text reads in English and Chinese", () => {
  const keys = ["energyNoteShortReview", "energyNoteHarderSession", "energyNoteHeavyLoad", "energyNoteBiggestWork", "energyNoteSmallStep",
    "energyNoteNextBigStep", "cellEnergy", "dayEnergy", "dayEnergyNone", "legendEnergy", "legendEnergyNote", "proposalEnergyTitle",
    "proposalEnergyReading", "proposalEnergyAverage", "proposalEnergyAverageNew", "proposalEnergyToday", "energyStepsLabel",
    "energyBarsLabel", "energyReadingsLine", "energyDayBar", "energyAverageLine", "energyLowestLine", "energyHighestLine",
    "energyTrendLine", "energyCompareLow", "energyCompareOther", "energyCompareArea", "energyCompareTooFew", "energyNoneReported",
    "planWhyHighEnergy"];
  for (const key of keys) {
    assert.ok(text.zh[key], `${key} in Chinese`);
    if (key !== "planWhyHighEnergy") assert.ok(text.en[key], `${key} in English`);
  }
  assert.equal(text.en.energyGuide, "2 or below suggests Lighter day, 4 or above Deep focus", "the plan by the name it shows");
});
