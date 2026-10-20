import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { taskDraft } from "../src/records/taskDraft.js";
import { scheduleOutside, yourDayProblem } from "../src/settings/schedule.js";
import { proposalView } from "../src/talk/proposal.js";
import { minutesOf } from "../src/time.js";
import { dayFrame, dayStrip, hourMarks } from "../src/today/stripLayout.js";
import { energySteps } from "../src/ui/visuals.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const say = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));
const en = say("en");
const zh = say("zh");
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const EARLY = { start: "07:00", end: "22:00" };
const USUAL = [{ title: "Lunch", start_time: "12:00", duration_minutes: 60 }, { title: "Dinner", start_time: "18:00", duration_minutes: 60 }];
const task = (start, minutes) => ({ kind: "item", id: start, start_time: start, duration_minutes: minutes, domain: "learning",
  completion_status: "planned" });

test("by default the strip runs 09:00–22:00, marked as before", () => {
  assert.deepEqual(dayFrame(), { start: minutesOf("09:00"), end: minutesOf("22:00") });
  assert.deepEqual(hourMarks(-100).map((mark) => mark.clock), ["09:00", "12:00", "15:00", "18:00", "22:00"]);
  assert.equal(dayStrip([task("07:30", 30)], minutesOf("07:00"), USUAL).tasks.length, 0, "a task before 09:00 is left off");
});

test("an early Your day draws from its start, marks its hours, and counts the time left to its end", () => {
  assert.deepEqual(dayFrame(EARLY), { start: minutesOf("07:00"), end: minutesOf("22:00") });
  assert.deepEqual(hourMarks(-100, EARLY).map((mark) => mark.clock), ["07:00", "10:00", "13:00", "16:00", "19:00", "22:00"]);
  const strip = dayStrip([task("07:30", 30)], minutesOf("07:00"), USUAL, { day: EARLY });
  assert.equal(strip.tasks.length, 1);
  assert.ok(strip.tasks[0].left > 0);
  assert.equal(strip.leftMinutes, minutesOf("22:00") - minutesOf("07:00"));
  assert.equal(dayStrip([], minutesOf("20:30"), USUAL, { day: { start: "09:00", end: "20:00" } }).leftMinutes, 0,
    "a day ended at 20:00 has nothing left at 20:30");
});

test("the strip's words name Your day, and every strip is given it", () => {
  assert.equal(en("dayStripDayOver", { time: "20:30", start: "09:00", end: "20:00" }), "Now 20:30 · today's 09:00–20:00 is over");
  assert.equal(zh("dayStripDayOver", { time: "20:30", start: "09:00", end: "20:00" }), "现在 20:30 · 今天的 09:00–20:00 已结束");
  assert.equal(en("dayStripSummary", { count: 2, open: "3 h", start: "07:00", end: "22:00" }),
    "The day from 07:00 to 22:00: 2 timed tasks, lunch and dinner kept free, 3 h open.");
  assert.match(source("today/DayStrip.jsx"), /dayStrip\(timed, whole \? frame\.start : now, dayMeals, \{ area, day \}\)/);
  assert.match(source("today/TodayScreen.jsx"), /<DayStrip timed=\{timed\} next=\{next\} now=\{now\} dayMeals=\{day\.meals \|\| \[\]\} day=\{day\.yourDay\}/);
  assert.equal((source("records/AreaCards.jsx").match(/day=\{day\.yourDay\}/g) || []).length, 2, "an area's day and the Life overview's");
});

test("energy steps lie across Your day", () => {
  assert.equal(energySteps([{ level: 3, time: "08:00" }], "22:00")[0].left, 0, "held at 09:00 by default");
  assert.ok(energySteps([{ level: 3, time: "08:00" }], "22:00", EARLY)[0].left > 0);
});

test("a new task's time starts at Your day's start", () => {
  assert.equal(taskDraft(null, "2026-10-20").startTime, "09:00");
  assert.equal(taskDraft(null, "2026-10-20", "life", "", "07:00").startTime, "07:00");
});

test("Your day is six hours or more, and the pane says when the work schedule goes beyond it", () => {
  assert.equal(yourDayProblem({ start: "09:00", end: "14:00" }), "yourDayTooShort");
  assert.equal(yourDayProblem({ start: "22:00", end: "09:00" }), "yourDayTooShort");
  assert.equal(yourDayProblem({ start: "07:00", end: "13:00" }), null);
  assert.equal(en("yourDayTooShort"), "Your day lasts at least 6 hours, its end after its start.");
  assert.equal(scheduleOutside({ enabled: true, start: "08:00", end: "17:00" }, { start: "09:00", end: "22:00" }), true);
  assert.equal(scheduleOutside({ enabled: true, start: "09:00", end: "17:00" }, { start: "09:00", end: "22:00" }), false);
  assert.equal(scheduleOutside({ enabled: false, start: "08:00", end: "17:00" }, { start: "09:00", end: "22:00" }), false);
  assert.equal(en("workScheduleOutsideDay", { start: "09:00", end: "22:00" }),
    "These hours go beyond your day, 09:00–22:00; plans use only the part inside it.");
  const pane = source("settings/ScheduleSection.jsx");
  assert.match(pane, /api\("\/api\/your-day", \{ method: "PUT", body: JSON\.stringify\(next\) \}\)/);
  assert.match(pane, /t\("yourDayTitle"\)/);
});

test("Ava's card setting Your day reads as the day it sets", () => {
  assert.deepEqual(proposalView({ actionType: "set_your_day", payload: { day: EARLY } }, []), { kind: "yourDay", date: null, day: EARLY });
  assert.match(source("talk/ProposalCard.jsx"), /view\.kind === "yourDay"/);
  assert.match(source("workspace.js"), /actionType === "set_your_day"/);
  assert.equal(en("proposalYourDayLine", { start: "07:00", end: "22:00" }), "Your day 07:00–22:00: plans fill it, and the day is over at 22:00.");
});

test("the pause card and the Life overview's free windows name Your day", () => {
  assert.equal(en("proposalPauseLine", { end: "20:00" }), "Nothing is current and no time counts until you resume it, or until 20:00.");
  assert.equal(en("noFreeWindows", { start: "07:00", end: "22:00" }), "No free window between 07:00 and 22:00.");
  assert.equal(en("shapeCounts", { start: "07:00", end: "22:00" }),
    "Booked time in every area, meals, and the free windows between 07:00 and 22:00.");
});
