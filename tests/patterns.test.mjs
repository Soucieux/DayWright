import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  bestHoursLead, bold, catchUpDay, cellLabel, checkPrompt, columnName, columnWhen, energyLead, estimatesLead, heatKey, keep, outcomeLead,
  paceLead, pairValue, pairsLead, rangeCaption, reportingLead, stateNote, taskPaceLine, timeText, toCheckNote,
} from "../src/patterns/patternText.js";
import { CHECK_TIMES_TITLES, proposalView } from "../src/talk/proposal.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
/** A sentence's text with September as "Sep", however this machine's dates abbreviate it ("Sep" or "Sept"). */
const sep = (value) => value.replace(/\bSept\b/g, "Sep");
const say = (language) => (key, values = {}) => {
  assert.ok(text[language][key], `${language} ${key}`);
  return sep(text[language][key].replace(/\{(\w+)\}/g, (match, name) => sep(String(values[name] ?? match))));
};
const en = say("en");
const zh = say("zh");
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
/** A sentence with its bold parts in ** marks, as bold() splits it. */
const marked = (parts) => parts.map((part) => (part.strong ? `**${part.text}**` : part.text)).join("");
const NB = " ";
// 2026-09-07 is a Monday; 2026-10-06 a Tuesday.
const WEEKS = [["2026-09-07", "2026-09-13"], ["2026-09-14", "2026-09-20"], ["2026-09-21", "2026-09-27"], ["2026-09-28", "2026-10-04"],
  ["2026-10-05", "2026-10-06"]].map(([start, end], index) => ({ start, end, kind: "week", current: index === 4 }));
const DAYS = ["2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06"]
  .map((day, index) => ({ start: day, end: day, kind: "day", current: index === 6 }));

test("a time never breaks across lines, and a finding's key figures are bold", () => {
  assert.equal(timeText(70, "en"), `1${NB}h${NB}10${NB}min`);
  assert.equal(keep("8 min"), `8${NB}min`);
  assert.deepEqual(bold("Work runs longest: **22% over plan**."), [{ text: "Work runs longest: ", strong: false },
    { text: "22% over plan", strong: true }, { text: ".", strong: false }]);
});

test("the range says its days and that it comes from the times you recorded; columns are named by their kind", () => {
  assert.equal(rangeCaption({ start: "2026-09-07", end: "2026-10-06" }, en, "en"), "7 Sep – 6 Oct · from the times you recorded");
  assert.equal(rangeCaption({ start: "2026-09-07", end: "2026-10-06" }, zh, "zh"), "9月7日 – 10月6日 · 来自你记录的用时");
  assert.equal(sep(columnName(WEEKS[0], WEEKS, "en")), "7 Sep");
  assert.equal(columnName(DAYS[6], DAYS, "en"), "T");
  assert.equal(columnName({ start: "2026-09-10", end: "2026-09-10", kind: "day" }, new Array(30), "en"), "10", "a month of days by their dates");
  assert.equal(sep(columnName({ start: "2026-09-01", end: "2026-09-30", kind: "month" }, [], "en")), "Sep");
  assert.equal(columnWhen(WEEKS[4], WEEKS, "2026-10-06", en, "en"), "this week");
  assert.equal(columnWhen(WEEKS[0], WEEKS, "2026-10-06", en, "en"), "in the week of 7 Sep");
  assert.equal(columnWhen(WEEKS[4], WEEKS, "2026-10-20", en, "en"), "in the week of 5 Oct", "a week before this one is named");
  assert.equal(columnWhen(DAYS[6], DAYS, "2026-10-06", en, "en"), "today");
  assert.equal(columnWhen(DAYS[0], DAYS, "2026-10-06", en, "en"), "on Wednesday");
  assert.equal(columnWhen({ start: "2026-09-01", end: "2026-09-30", kind: "month" }, [], "2026-10-06", en, "en"), "in September");
});

test("every state has its words: not enough yet with how far along, still settling, nothing in range", () => {
  const few = stateNote("bestHours", { state: "few", count: 3, threshold: 10, unit: "tasks", basis: 3 }, "month", en);
  assert.equal(few.text, "Best hours appears after 10 fully done tasks with real times. 3 so far.");
  assert.deepEqual(few.progress, { count: 3, threshold: 10, text: "3 of 10" });
  const settling = stateNote("estimates", { state: "settling", count: 4, threshold: 3, unit: "days", basis: 4 }, "month", en);
  assert.equal(settling.chip, "Based on 4 days · still settling");
  assert.equal(stateNote("plannedActual", { state: "settling", count: 3, threshold: 3, unit: "tasks", basis: 9 }, "week", en).chip,
    "Based on 9 tasks · still settling");
  assert.equal(stateNote("outcome", { state: "empty", count: 0, threshold: 2, unit: "days", basis: 0 }, "week", en).text,
    "Nothing recorded this week. Try Month or All time.");
  assert.equal(stateNote("outcome", { state: "empty", count: 0, threshold: 2, unit: "days", basis: 0 }, "all", en).text,
    "Time by outcome appears after 2 days with recorded times. 0 so far.");
  assert.equal(stateNote("reporting", { state: "ready", count: 9, threshold: 3, unit: "days", basis: 9 }, "month", en).state, "ready");
  assert.equal(toCheckNote(2, 0, en), "2 times to check are left out of these graphs");
  assert.equal(toCheckNote(1, 0, en), "1 time to check is left out of these graphs");
  assert.equal(toCheckNote(1, 0, zh), "有 1 个待核对的用时未计入这些图表");
  for (const key of ["patternsServiceOff", "patternsLoading", "patternsTab", "patternsAskAva"]) en(key);
  assert.equal(en("patternsServiceOff"), "Patterns appear while the local service is running.");
});

test("best hours: the best window and day, ties, one hour, the cell's words and the key in counts", () => {
  assert.equal(marked(bestHoursLead({ kind: "window", from: 10, to: 12, day: 1 }, en, "en")),
    "You finish most between **10:00 and 12:00**, and most on **Tuesdays**.");
  assert.equal(marked(bestHoursLead({ kind: "windows", hours: [10, 15], day: null }, en, "en")), "You finish most at **10:00** and at **15:00**.");
  assert.equal(marked(bestHoursLead({ kind: "oneHour", hour: 10 }, en, "en")), "All your finishes so far were at **10:00**.");
  assert.equal(marked(bestHoursLead({ kind: "window", from: 10, to: 12, day: 1 }, zh, "zh")), "你最常在 **10:00 到 12:00** 完成任务，最常在**周二**。");
  assert.equal(cellLabel(4, 10, 3, en, "en"), "Fri 10:00–11:00 · 3 tasks finished");
  assert.equal(cellLabel(4, 10, 1, en, "en"), "Fri 10:00–11:00 · 1 task finished");
  assert.equal(cellLabel(4, 10, 0, en, "en"), "Fri 10:00–11:00 · none");
  assert.deepEqual(heatKey([{ step: 1, from: 1, to: 1 }, { step: 2, from: 2, to: 3 }], en), { steps: ["1", "2–3"], unit: "tasks an hour" });
});

test("planned against actual: by area and by repeating task", () => {
  assert.equal(marked(pairsLead({ kind: "over", key: "work", title: null, percent: 22 }, en, "en")), "Work runs longest: **22% over plan**.");
  assert.equal(marked(pairsLead({ kind: "under", key: "life", title: null, percent: -5 }, en, "en")), "Life finishes **5% under plan**.");
  assert.equal(marked(pairsLead({ kind: "close" }, en, "en")), "Your plans are close: every area within 10%.");
  assert.equal(marked(pairsLead({ kind: "usual", key: "s1", title: "Weekly review", actual: 75, planned: 60 }, en, "en")),
    `Weekly review usually takes **75${NB}min**; you set 60.`);
  assert.equal(marked(pairsLead({ kind: "close" }, en, "en", true)), "Your repeating tasks run close to plan: each within 10%.");
  assert.deepEqual(pairValue({ planned: 50, actual: 55, percent: 10, count: 7 }, en, "en"),
    { value: `50 → 55${NB}min`, detail: "+10% · 7 done", needs: null });
  assert.equal(pairValue({ planned: 40, actual: 38, percent: -5, count: 12 }, en, "en").detail, "−5% · 12 done");
  assert.equal(pairValue({ planned: null, actual: null, percent: null, count: 1 }, en, "en").needs, "Needs 3 fully done · 1 so far");
});

test("estimates improving: down, up, about the same, spot on, one column, by week and by day", () => {
  assert.equal(marked(estimatesLead({ kind: "down", now: 8, before: 25, column: 4, beforeColumn: 0 }, WEEKS, "2026-10-06", en, "en")),
    `This week's estimates are **8${NB}min off**, down from 25 in the week of 7 Sep.`);
  assert.equal(marked(estimatesLead({ kind: "up", now: 15, before: 10, column: 5, beforeColumn: 0 }, DAYS, "2026-10-06", en, "en")),
    `Monday's estimates were **15${NB}min off**, up from 10 on Wednesday.`);
  assert.equal(marked(estimatesLead({ kind: "same", now: 10, before: 11, column: 4, beforeColumn: 0 }, WEEKS, "2026-10-06", en, "en")),
    `About the same as before: **10${NB}min off**.`);
  assert.equal(marked(estimatesLead({ kind: "spot", now: 0, before: 9, column: 4, beforeColumn: 0 }, WEEKS, "2026-10-06", en, "en")),
    "Spot on: estimates matched the real time.");
  assert.equal(marked(estimatesLead({ kind: "single", now: 8, column: 4 }, WEEKS, "2026-10-06", en, "en")),
    `This week's estimates are **8${NB}min off**.`);
  assert.equal(marked(estimatesLead({ kind: "down", now: 8, before: 25, column: 4, beforeColumn: 0 }, WEEKS, "2026-10-06", zh, "zh")),
    `本周估时偏差 **8${NB}分钟**，比9月7日那周的 25 分钟少。`);
});

test("time by outcome, energy and real time, reporting habit and section pace say what they found", () => {
  assert.equal(marked(outcomeLead({ share: 86, noReply: 70 }, en, "en")),
    `**86%** of your time went to tasks you fully finished; 1${NB}h${NB}10${NB}min went to tasks left without a status.`);
  assert.equal(marked(outcomeLead({ share: 100, noReply: 0 }, en, "en")), "**100%** of your time went to tasks you fully finished.");
  assert.equal(marked(energyLead({ kind: "longer", group: "low", percent: 20 }, en)), "On low-energy days tasks run **20% longer** than planned.");
  assert.equal(marked(energyLead({ kind: "shorter", group: "high", percent: -10 }, en)), "On high-energy days tasks run **10% shorter** than planned.");
  assert.equal(marked(energyLead({ kind: "longer", group: "low", percent: 20 }, en, true)), "On low-energy days tasks run **20% longer**.");
  assert.equal(marked(energyLead({ kind: "hardly" }, en)), "Your energy hardly changes how long tasks take.");
  assert.equal(marked(energyLead({ kind: "never" }, en)), "Energy is optional. Report it on Today to see how it changes your times.");
  assert.equal(marked(reportingLead({ now: 80, before: 60, column: 4, beforeColumn: 0, noReply: 2 }, WEEKS, "2026-10-06", en, "en")),
    "**80%** of statuses were set right away this week, up from 60% in the week of 7 Sep. 2 tasks got no status.");
  assert.equal(marked(reportingLead({ now: 60, before: 60, column: 4, beforeColumn: 0, noReply: 0 }, WEEKS, "2026-10-06", en, "en")),
    "**60%** of statuses were set right away this week, as in the week of 7 Sep.");
  assert.equal(marked(reportingLead({ now: 50, before: null, column: 6, beforeColumn: null, noReply: 1 }, DAYS, "2026-10-06", en, "en")),
    "**50%** of statuses were set right away today. 1 task got no status.");
  assert.equal(marked(paceLead({ kind: "fastest", title: "Directives", minutes: 8 }, en, "en")), `Directives goes fastest: about **8${NB}min a section**.`);
  assert.equal(marked(paceLead({ kind: "one", title: "Directives", minutes: 8 }, en, "en")), `Directives: about **8${NB}min a section**.`);
});

test("a learning task says what its sections left will take, once its source has a pace", () => {
  const pace = { minutes: 12, sections: 5 };
  assert.equal(marked(taskPaceLine(pace, { done: 2, total: 5 }, 60, en, "en")), `About **12${NB}min a section**, roughly 36${NB}min left (3 sections).`);
  assert.equal(marked(taskPaceLine(pace, { done: 4, total: 5 }, 60, en, "en")), `About 12${NB}min left (1 section).`);
  assert.equal(marked(taskPaceLine(pace, { done: 5, total: 5 }, 60, en, "en")), "All sections ticked.");
  assert.equal(marked(taskPaceLine({ minutes: 20, sections: 4 }, { done: 2, total: 5 }, 45, en, "en")),
    `About 60${NB}min left, more than this task's 45${NB}min.`);
  assert.equal(taskPaceLine(null, { done: 2, total: 5 }, 45, en, "en"), null, "hidden until its source has a pace");
});

test("the note counts every time left out, including tasks that need a status first, and offers Catch up beside Ask Ava", () => {
  assert.equal(toCheckNote(3, 1, en), "3 times to check are left out of these graphs · 1 needs a status first");
  assert.equal(toCheckNote(3, 2, en), "3 times to check are left out of these graphs · 2 need a status first");
  assert.equal(toCheckNote(1, 1, en), "1 time to check is left out of these graphs · 1 needs a status first");
  assert.equal(toCheckNote(3, 1, zh), "有 3 个待核对的用时未计入这些图表 · 其中 1 项需先补记状态");
  assert.equal(toCheckNote(3, 2, zh), "有 3 个待核对的用时未计入这些图表 · 其中 2 项需先补记状态");
  // Catch up starts at the earliest day with a task needing a status; none, and there's no Catch up.
  const checks = [{ date: "2026-10-01", needsStatus: false }, { date: "2026-10-03", needsStatus: true }, { date: "2026-10-05", needsStatus: true }];
  assert.equal(catchUpDay(checks), "2026-10-03");
  assert.equal(catchUpDay([{ date: "2026-10-01", needsStatus: false }]), null);
  assert.equal(catchUpDay(undefined), null);
  const panel = source("patterns/PatternsPanel.jsx");
  assert.match(panel, /toCheckNote\(tab\.toCheck, tab\.needsStatus, t\)/);
  assert.match(panel, /onAskAva\(checkPrompt\(tab\.period, t\), true\)/);
  assert.match(panel, /tab\.needsStatus > 0 && \(\s*<button[^>]*onClick=\{\(\) => onAskAva\(t\("catchUpPrompt"\), true, catchUpDay\(tab\.checks\)\)\}>\s*\{t\("catchUpAction"\)\}/);
  // A request sent at once may name its day, and Ava answers it from that day.
  assert.match(source("App.jsx"), /function askAva\(text, send = false, date = null\) \{\s*if \(text\) setConversationPrompt\(\{ id: Date\.now\(\), text, send, date \}\);/);
  const talk = source("talk/TalkPanel.jsx");
  assert.match(talk, /send\(prompt\.text, prompt\.date \|\| day\.date\)/);
  assert.match(talk, /async function send\(text, on = day\.date\) \{/);
  assert.match(talk, /body: JSON\.stringify\(\{ date: on, message: words,/);
});

test("Ask Ava from Patterns lists the same times as the note, for the days it shows, each row with its day", () => {
  // The words match the service's: the days shown, or every time on All time.
  assert.deepEqual(["week", "month", "all"].map((period) => checkPrompt(period, en)),
    ["Check my times for these 7 days", "Check my times for these 30 days", "Check all my times"]);
  assert.deepEqual(["week", "month", "all"].map((period) => checkPrompt(period, zh)), ["核对这 7 天的用时", "核对这 30 天的用时", "核对我所有的用时"]);
  const tasks = [{ itemId: "a", date: "2026-10-06", title: "Read", start: null, end: null, minutes: null, setMinutes: 60, needsStatus: true }];
  assert.deepEqual(proposalView({ actionType: "check_times", payload: { date: null, period: "week", tasks } }, []),
    { kind: "checkTimes", date: null, period: "week", tasks });
  assert.deepEqual(CHECK_TIMES_TITLES, { week: "proposalCheckTimesWeekTitle", month: "proposalCheckTimesMonthTitle" });
  assert.deepEqual([en("proposalCheckTimesWeekTitle"), en("proposalCheckTimesMonthTitle"), en("proposalCheckTimesAllTitle")],
    ["Check times from these 7 days", "Check times from these 30 days", "Check your times"]);
  assert.deepEqual([zh("proposalCheckTimesWeekTitle"), zh("proposalCheckTimesMonthTitle"), zh("proposalCheckTimesAllTitle")],
    ["核对这 7 天的用时", "核对这 30 天的用时", "核对你的用时"]);
  const card = source("talk/ProposalCard.jsx");
  assert.match(card, /view\.date \? t\("proposalCheckTimesTitle", \{ when \}\) : t\(CHECK_TIMES_TITLES\[view\.period\] \|\| "proposalCheckTimesAllTitle"\)/);
  assert.match(card, /<CheckTimesList tasks=\{view\.tasks\} dated=\{!view\.date\} checks=\{checks\} onCatchUp=\{onCatchUp\}/);
  assert.match(card, /dated \? `\$\{shortDate\(task\.date, language\)\} · ` : ""/);
  // A task that still needs a status shows as needing one, with Catch up, rather than Right or Change.
  assert.match(card, /if \(task\.needsStatus\) \{/);
  assert.match(card, /t\("checkTimeNeedsStatus"\)/);
  assert.match(card, /aria-label=\{t\("checkTimeCatchUpFor", \{ title \}\)\} onClick=\{\(\) => onCatchUp\(task\.date\)\}>\{t\("catchUpAction"\)\}/);
  assert.match(source("talk/TalkPanel.jsx"), /onCatchUp=\{\(on\) => send\(t\("catchUpPrompt"\), on\)\}/);
  assert.deepEqual([en("checkTimeNeedsStatus"), zh("checkTimeNeedsStatus")],
    ["Needs a status before its time can be checked", "需先补记状态，才能核对用时"]);
  assert.deepEqual([en("checkTimeCatchUpFor", { title: "Read" }), zh("checkTimeCatchUpFor", { title: "Read" })],
    ["Catch up on the day of Read", "补记“Read”那天"]);
  // Confirmed, a card with no one day refreshes the day on show, and Patterns reads its times again.
  assert.match(source("workspace.js"), /const touched = changedDate \|\| \(actionType === "check_times" \? day\.date : null\);/);
  assert.match(source("calendar/CalendarScreen.jsx"), /<PatternsPanel date=\{day\.date\} stamp=\{day\}/);
  assert.match(source("patterns/PatternsPanel.jsx"), /\}, \[date, period, backendConnected, stamp\]\);/);
});

test("every new Patterns text exists in both languages, and a finding starts at the edge rather than spreading out", () => {
  const keys = Object.keys(text.en).filter((key) => /^(patterns?|threshold)[A-Z]/.test(key));
  assert.ok(keys.length > 40, String(keys.length));
  for (const key of keys) assert.ok(text.zh[key], key);
  assert.deepEqual(["patternBestHours", "patternPairs", "patternEstimates", "patternOutcome", "patternPace", "patternEnergy", "patternReporting"]
    .map((key) => text.zh[key]), ["最佳时段", "计划与实际", "估时越来越准", "时间去向", "章节节奏", "精力与用时", "汇报习惯"]);
  assert.match(source("bench.css"), /\.dw-pattern-lead,[^{]*\{[^}]*text-align: start/);
});
