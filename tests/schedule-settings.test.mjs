import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { PANES } from "../src/settings/panes.js";
import { countryName, countryOptions, holidayDate, holidayName, importedLine, regionName, regionOptions, scheduleProblem }
  from "../src/settings/schedule.js";
import { proposalView } from "../src/talk/proposal.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const say = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));
const en = say("en");
const zh = say("zh");
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const NAMES = { "CA-AB": { en: "Alberta", zh: "艾伯塔省" }, "CA-ON": { en: "Ontario", zh: "安大略省" }, "US-CA": { en: "California" } };

test("Settings gains a Schedule pane, with the calendar icon, before Demo", () => {
  assert.deepEqual(PANES.map(([id]) => id), ["models", "memory", "schedule", "demo"]);
  assert.deepEqual(PANES[2], ["schedule", "settingsSchedule", "calendar"]);
  assert.deepEqual([en("settingsSchedule"), zh("settingsSchedule")], ["Schedule", "日程"]);
  assert.match(source("settings/SettingsSheet.jsx"),
    /\{shown === "schedule" && <ScheduleSection backendConnected=\{backendConnected\} onChanged=\{onChanged\} \/>\}/);
});

test("countries are named in the interface's language and listed by name", () => {
  assert.equal(countryName("CA", "en"), "Canada");
  assert.equal(countryName("CA", "zh"), "加拿大");
  assert.deepEqual(countryOptions(["DE", "CA", "AT"], "en"), [{ value: "AT", label: "Austria" }, { value: "CA", label: "Canada" },
    { value: "DE", label: "Germany" }]);
});

test("regions are named where DayWright knows them, else by code, with national holidays alone first", () => {
  assert.equal(regionName("CA-ON", NAMES, "zh"), "安大略省");
  assert.equal(regionName("US-CA", NAMES, "zh"), "California", "the English name where there is no Chinese one");
  assert.equal(regionName("CA-QC", NAMES, "en"), "CA-QC");
  assert.deepEqual(regionOptions(["CA-ON", "CA-AB"], NAMES, "en", en), [{ value: "", label: "National holidays only" },
    { value: "CA-AB", label: "Alberta" }, { value: "CA-ON", label: "Ontario" }]);
});

test("a holiday is named in Chinese by its local name when that is written in Chinese", () => {
  const spring = { name: "Chinese New Year (Spring Festival)", localName: "春节" };
  assert.equal(holidayName(spring, "zh"), "春节");
  assert.equal(holidayName(spring, "en"), "Chinese New Year (Spring Festival)");
  assert.equal(holidayName({ name: "Saint-Jean-Baptiste Day", localName: "Fête nationale du Québec" }, "zh"), "Saint-Jean-Baptiste Day");
  assert.equal(holidayDate("2026-10-12", "en"), "Mon, 12 Oct 2026", "the list holds two years, so each date has its year");
});

test("a work schedule is kept whole: an end after its start, and at least one day", () => {
  assert.equal(scheduleProblem({ start: "09:00", end: "17:00", days: [0] }), null);
  assert.equal(scheduleProblem({ start: "17:00", end: "09:00", days: [0] }), "workScheduleEndAfterStart");
  assert.equal(scheduleProblem({ start: "", end: "09:00", days: [0] }), "workScheduleEndAfterStart");
  assert.equal(scheduleProblem({ start: "09:00", end: "17:00", days: [] }), "workScheduleNeedsDay");
  assert.equal(en("workScheduleEndAfterStart"), "The end comes after the start.");
});

test("Settings says when the holidays were imported, and that DayWright goes online for them only on Import", () => {
  const view = { importedAt: "2026-10-19T14:00:00+00:00", years: [2026, 2027] };
  assert.equal(importedLine(view, en, "en"), "Last imported 19 October 2026, for 2026 and 2027.");
  assert.equal(importedLine(view, zh, "zh"), "上次导入：2026年10月19日，涵盖 2026 和 2027 年。");
  assert.equal(importedLine({ importedAt: null, years: [] }, en, "en"), "Not imported yet. Choose the country, then Import.");
  assert.equal(en("holidaysPrivacy"), "DayWright contacts date.nager.at only when you click Import.");
  assert.equal(zh("holidaysPrivacy"), "只有在你点击“导入”时，DayWright 才会连接 date.nager.at。");
});

test("the Schedule pane has two switches, and goes online only through its Import button", () => {
  const pane = source("settings/ScheduleSection.jsx");
  assert.equal((pane.match(/role="switch"/g) || []).length, 2, "the work schedule and statutory holidays");
  assert.match(pane, /api\("\/api\/schedule", \{ method: "PUT", body: JSON\.stringify\(next\) \}\)/);
  assert.match(pane, /api\("\/api\/holidays", \{ method: "PUT", body: JSON\.stringify\(next\) \}\)/);
  assert.equal((pane.match(/\/api\/holidays\/import/g) || []).length, 1);
  assert.match(pane, /api\("\/api\/holidays\/import", \{ method: "POST" \}\)/);
  assert.match(pane, /onClick=\{importHolidays\}/, "Import alone fetches");
  assert.match(pane, /api\("\/api\/holidays", \{ method: "DELETE" \}\)/);
  assert.match(pane, /<MenuSelect label=\{t\("holidaysCountry"\)\}/);
  assert.match(pane, /<MenuSelect label=\{t\("holidaysRegion"\)\}/);
});

test("Today names a holiday in its header, and from 1 December reminds the user to import next year's", () => {
  const today = source("today/TodayScreen.jsx");
  assert.match(today, /\{day\.holiday && <span className="dw-chip dw-chip-holiday"><Icon name="calendar" size=\{14\} \/>\{t\("holidayChip", \{ name: holidayName\(day\.holiday, language\) \}\)\}<\/span>\}/);
  assert.match(today, /day\.holidayReminder/);
  assert.match(today, /openSettings\("schedule"\)/);
  assert.equal(en("holidayChip", { name: "Thanksgiving" }), "Thanksgiving · statutory holiday");
  assert.equal(zh("holidayChip", { name: "春节" }), "春节 · 法定假日");
  assert.equal(en("holidayReminderTitle", { year: 2027 }), "Import 2027's holidays");
  assert.equal(zh("holidayReminderTitle", { year: 2027 }), "导入 2027 年的假日");
});

test("the Calendar marks a holiday's cell, its legend and its day panel", () => {
  const calendar = source("calendar/CalendarScreen.jsx");
  assert.match(calendar, /holiday && t\("cellHoliday", \{ name: holidayName\(holiday, language\) \}\)/);
  assert.match(calendar, /className="dw-cal-label dw-cal-holiday"/);
  assert.match(calendar, /\["legendHoliday", "dw-mark-holiday", "calendar"\]/);
  assert.match(source("calendar/DayPanel.jsx"), /day\.holiday &&/);
  assert.match(source("App.jsx"), /holidays=\{calendarHolidays\}/);
});

test("a task placed inside working hours says so on its sheet, and still saves", () => {
  assert.match(source("records/TaskSheet.jsx"), /task\?\.workingHours && \(/);
  assert.equal(en("taskInWorkingHours", { start: "09:00", end: "17:00" }),
    "Inside your working hours, 09:00–17:00. It saves as you placed it; plans keep these hours free.");
});

test("Ava's schedule and holiday cards read as what they change", () => {
  const schedule = { enabled: true, mode: "working", start: "09:00", end: "18:00", days: [0, 1, 2, 3, 4] };
  assert.deepEqual(proposalView({ actionType: "set_schedule", payload: { schedule } }, []), { kind: "schedule", date: null, schedule });
  const ontario = { en: "Ontario", zh: "安大略省" };
  assert.deepEqual(proposalView({ actionType: "import_holidays", payload: { country: "CA", region: "CA-ON", regionName: ontario,
    years: [2026, 2027], source: "date.nager.at" } }, []), { kind: "importHolidays", date: null, country: "CA", region: "CA-ON",
    regionName: ontario, years: [2026, 2027], source: "date.nager.at" });
  const card = source("talk/ProposalCard.jsx");
  assert.match(card, /view\.kind === "schedule"/);
  assert.match(card, /view\.kind === "importHolidays"/);
  assert.equal(en("proposalHolidaysSource", { source: "date.nager.at" }),
    "When you confirm, DayWright contacts date.nager.at once to fetch them, and holidays are on.");
  assert.match(source("workspace.js"), /actionType === "set_schedule" \|\| actionType === "set_your_day" \|\| actionType === "import_holidays"/);
});

test("plans say in English and Chinese how they keep the work schedule and a holiday", () => {
  const planner = readFileSync(new URL("../backend/app/planner.py", import.meta.url), "utf8");
  for (const key of ["planScheduleWorking", "planScheduleFocus", "planHoliday"]) {
    assert.ok(planner.includes(`"${key}": "${text.en[key]}"`), `${key} reads as the service's own words`);
  }
  assert.equal(zh("planScheduleWorking", { start: "09:00", end: "17:00" }), "留出你的工作时间 09:00–17:00。");
  assert.equal(zh("planScheduleFocus", { start: "09:00", end: "12:00" }), "把工作任务安排在你的专注时间 09:00–12:00 内。");
  assert.equal(zh("planHoliday", { name: "Thanksgiving" }), "Thanksgiving是法定假日：工作安排不适用，工作类重复任务也不带入。");
});
