import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  GOALS_SHOWN, allDoneText, moreGoalsText, projectLineText, projectOrder, shownGoals, stepsText, subjectNextText, subjectOrder,
  subjectTimeText,
} from "../src/records/areaOverview.js";
import { interfaceText } from "./interfaceText.mjs";

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);
const text = interfaceText();
/** The interface's own text lookup, in one language: its message with the values put in. */
const words = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (_, name) => values[name]);
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

test("Subjects lists goals with time this week first, most planned first, then the most recently practised; paused goals last", () => {
  const subject = (goalId, plannedMinutes, doneMinutes, lastPractised, status = "active") => (
    { goalId, plannedMinutes, doneMinutes, lastPractised, status });
  const order = subjectOrder([
    subject("idle-old", 0, 0, "2026-09-01"), subject("small", 30, 0, null), subject("paused-big", 300, 120, "2026-10-09", "paused"),
    subject("big", 150, 90, "2026-10-08"), subject("idle-recent", 0, 0, "2026-10-06"), subject("never", 0, 0, null),
    subject("tie-early", 60, 0, "2026-10-01"), subject("tie-late", 60, 30, "2026-10-05"), subject("paused-idle", 0, 0, null, "paused"),
  ]);
  assert.deepEqual(order.map((entry) => entry.goalId),
    ["big", "tie-late", "tie-early", "small", "idle-recent", "idle-old", "never", "paused-big", "paused-idle"]);
});

test("Projects lists the soonest next step first, then stalled goals, then the rest; paused goals last", () => {
  const project = (goalId, health, next) => ({ goalId, health, nextStep: next && { title: "Step", date: next } });
  const order = projectOrder([
    project("rest", "on-track", null), project("stalled", "stalled", null), project("later", "on-track", "2026-10-14"),
    project("paused", "paused", "2026-10-11"), project("soon", "stalled", "2026-10-10"), project("none", "no-steps", null),
  ]);
  assert.deepEqual(order.map((entry) => entry.goalId), ["soon", "later", "stalled", "rest", "none", "paused"]);
});

test("each card lists its first 6 goals, then + N more goals, and all of them once opened out", () => {
  const goals = Array.from({ length: 10 }, (_, index) => ({ goalId: `goal-${index}` }));
  assert.equal(GOALS_SHOWN, 6);
  assert.deepEqual(shownGoals(goals, false), { shown: goals.slice(0, 6), more: 4 });
  assert.deepEqual(shownGoals(goals, true), { shown: goals, more: 4 });
  assert.deepEqual(shownGoals(goals.slice(0, 6), false), { shown: goals.slice(0, 6), more: 0 });
  assert.equal(moreGoalsText(4, t), 'moreGoals {"count":4}');
  assert.equal(moreGoalsText(1, t), "moreGoalOne");
  assert.deepEqual([text.en.moreGoals, text.en.moreGoalOne, text.en.fewerGoals], ["+ {count} more goals", "+ 1 more goal", "Show fewer"]);
  assert.deepEqual([text.zh.moreGoals, text.zh.moreGoalOne, text.zh.fewerGoals], ["还有 {count} 个目标", "还有 1 个目标", "收起"]);
});

test("a subject's second line says its next task to study with its place and day, that all are done, or that it has none yet", () => {
  const next = { title: "Task 2 essay", number: 4, date: "2026-10-09", start_time: null };
  // Split around its title, so a narrow card cuts the title alone and keeps its place and day whole.
  assert.deepEqual(subjectNextText({ tasks: { total: 9, next } }, words("en"), "en"),
    { head: "Next: ", title: "Task 2 essay", tail: " (4 of 9) · Fri 9 Oct" });
  assert.deepEqual(subjectNextText({ tasks: { total: 9, next: { ...next, start_time: "18:00" } } }, words("en"), "en"),
    { head: "Next: ", title: "Task 2 essay", tail: " (4 of 9) · Fri 9 Oct 18:00" });
  assert.deepEqual(subjectNextText({ tasks: { total: 9, next } }, words("zh"), "zh"),
    { head: "下一个：", title: "Task 2 essay", tail: "（第 4 个，共 9 个）· 10月9日周五" });
  assert.deepEqual(subjectNextText({ tasks: { total: 5, next: null } }, words("en"), "en"), { head: "All 5 done", title: "", tail: "" });
  assert.deepEqual(subjectNextText({ tasks: { total: 1, next: null } }, words("en"), "en"), { head: "Its 1 task is done", title: "", tail: "" });
  assert.deepEqual(subjectNextText({ tasks: null }, words("zh"), "zh"), { head: "还没有任务", title: "", tail: "" });
  assert.deepEqual([text.en.subjectNextLine, text.en.allTasksDone, text.en.noTasksYet],
    ["Next: {title} ({number} of {total}) · {when}", "All {total} done", "No tasks yet"]);
  assert.deepEqual([text.zh.subjectNextLine, text.zh.allTasksDone, text.zh.noTasksYet],
    ["下一个：{title}（第 {number} 个，共 {total} 个）· {when}", "{total} 个都已完成", "还没有任务"]);
});

test("a goal whose only task is done says Its 1 task is done, on the card and in the sheet", () => {
  assert.equal(allDoneText(1, words("en")), "Its 1 task is done");
  assert.equal(allDoneText(1, words("zh")), "它的 1 个任务已完成");
  assert.equal(allDoneText(4, words("en")), "All 4 done");
  const week = source("records/GoalsScreen.jsx");
  assert.match(week.slice(week.indexOf("function GoalWeek")), /allDoneText\(week\.tasks\.total, t\)/);
});

test("a project's second line says its next step and day, else its last step, else that it has no next step", () => {
  const step = (title, date) => ({ title, date });
  assert.deepEqual(projectLineText({ nextStep: step("Draft", "2026-10-10"), lastStep: step("Outline", "2026-10-08") }, words("en"), "en"),
    { head: "Next: ", title: "Draft", tail: " · Sat 10 Oct" });
  assert.deepEqual(projectLineText({ nextStep: null, lastStep: step("Outline", "2026-10-08") }, words("en"), "en"),
    { head: "Last step: ", title: "Outline", tail: " · Thu 8 Oct" });
  assert.deepEqual(projectLineText({ nextStep: null, lastStep: step("Outline", "2026-10-08") }, words("zh"), "zh"),
    { head: "上一步：", title: "Outline", tail: " · 10月8日周四" });
  assert.deepEqual(projectLineText({ nextStep: null, lastStep: null }, words("en"), "en"), { head: "No next step yet", title: "", tail: "" });
  assert.deepEqual([text.en.nextStepLabel, text.en.stepsDone], ["Next: {title} · {date}", "{done} of {total} steps"]);
  assert.deepEqual([text.zh.nextStepLabel, text.zh.stepsDone], ["下一步：{title} · {date}", "{done} / {total} 步"]);
});

test("a narrow line cuts only its title with …; its place and day stay whole", () => {
  const cards = source("records/AreaCards.jsx");
  const line = cards.slice(cards.indexOf("function TitleLine"), cards.indexOf("\n}\n", cards.indexOf("function TitleLine")));
  assert.match(line, /<span className="dw-goal-line-title">\{line\.title\}<\/span>/);
  const css = source("bench.css");
  assert.match(css, /\.dw-goal-line-title \{ min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; \}/);
  assert.match(css, /\.dw-goal-line-fixed \{ flex: none; white-space: pre; \}/);
  // No gap between its parts: a link's own gap would double the spaces they carry.
  assert.match(css, /\.dw-goal-line-text \{ display: flex; gap: 0; min-width: 0; text-align: left; \}/);
  // On a phone a subject's line goes under its dots, where its place and day fit, in Chinese too.
  const phone = css.slice(css.indexOf("@media (max-width: 640px)", css.indexOf(".dw-goal-line-fixed")));
  assert.match(phone, /\.dw-goal-line \{ flex-wrap: wrap; row-gap: 2px; \}/);
  assert.match(phone, /\.dw-goal-line \.dw-tip-wrap \+ \.dw-goal-line-text \{ flex-basis: 100%; \}/);
});

test("a week with nothing planned and nothing done reads None this week, on a goal and on Not in a goal", () => {
  assert.equal(subjectTimeText({ plannedMinutes: 0, doneMinutes: 0 }, words("en"), "en"), "None this week");
  assert.equal(subjectTimeText({ plannedMinutes: 0, doneMinutes: 0 }, words("zh"), "zh"), "本周没有安排");
  assert.equal(subjectTimeText({ plannedMinutes: 150, doneMinutes: 60 }, words("en"), "en"), "1 h of 2 h 30 min");
  const subjects = source("records/AreaCards.jsx").slice(source("records/AreaCards.jsx").indexOf("export function SubjectsCard"));
  assert.match(subjects, /subjectTimeText\(subject, t, language\)/);
  assert.match(subjects, /subjectTimeText\(data\.other, t, language\)/);
});

test("each compact dot shows its day and state as a tip, on hover and keyboard focus, from its accessible name", () => {
  const visuals = source("ui/AreaVisuals.jsx");
  const dots = visuals.slice(visuals.indexOf("export function PracticeDots"), visuals.indexOf("\n}\n", visuals.indexOf("export function PracticeDots")));
  assert.match(dots, /<GraphTips label=\{label\}>/);
  assert.match(dots, /data-mark aria-label=\{`\$\{shortDate\(dates\[index\], language\)\} · \$\{t\(PRACTICE_DAY_TEXT\[dot\.state\]\)\}`\}/);
  assert.doesNotMatch(dots, /letters\[index\]/, "the weekday letters are gone; the tip names the day");
});

test("a project's steps read 5 of 8 steps, or 0 of 1 step", () => {
  assert.equal(stepsText({ done: 5, total: 8 }, t), 'stepsDone {"done":5,"total":8}');
  assert.equal(stepsText({ done: 0, total: 1 }, t), 'stepsDoneOne {"done":0}');
  assert.deepEqual([text.en.stepsDoneOne, text.zh.stepsDoneOne], ["{done} of 1 step", "{done} / 1 步"]);
});

test("Subjects and Projects show one compact entry per goal, in their order, with the first 6 and + N more", () => {
  const cards = source("records/AreaCards.jsx");
  for (const [card, order] of [["SubjectsCard", "subjectOrder"], ["ProjectsCard", "projectOrder"]]) {
    const body = cards.slice(cards.indexOf(`export function ${card}`), cards.indexOf("\n}\n", cards.indexOf(`export function ${card}`)));
    assert.match(body, new RegExp(`<GoalLines goals=\\{${order}\\(`), `${card} draws its goals in order as compact entries`);
  }
  const lines = cards.slice(cards.indexOf("function GoalLines"), cards.indexOf("\n}\n", cards.indexOf("function GoalLines")));
  assert.match(lines, /shownGoals\(goals, all\)/, "the first 6 goals, or all once opened out");
  assert.match(lines, /moreGoalsText\(more, t\)/, "+ N more goals");
  assert.match(lines, /aria-expanded=\{all\}/);
  const subjects = cards.slice(cards.indexOf("export function SubjectsCard"), cards.indexOf("export function PracticeCard"));
  assert.match(subjects, /<PracticeDots days=\{subject\.days\}/, "a subject's week is its 7 small dots");
  assert.match(subjects, /subjectNextText\(/);
  assert.match(subjects, /notInAGoal/, "the Not in a goal line stays");
  assert.doesNotMatch(subjects, /askAvaToPlanIt|lastPractisedOn|checklistProgress/, "these moved into the goal's sheet");
  const projects = cards.slice(cards.indexOf("export function ProjectsCard"), cards.indexOf("export function NextStepsCard"));
  assert.match(projects, /<StepBar /);
  assert.match(projects, /stepsText\(project, t\)/);
  assert.match(projects, /projectLineText\(/);
});

test("a Learning goal's sheet, opened from Learn, holds what left the card under This week, with Ask Ava to plan it", () => {
  const sheet = source("records/GoalsScreen.jsx");
  const week = sheet.slice(sheet.indexOf("function GoalWeek"), sheet.indexOf("\n}\n", sheet.indexOf("function GoalWeek")));
  for (const key of ["thisWeekHeading", "lastPractisedOn", "notPractisedYet", "nextSessionLabel", "noSessionPlanned", "nextStudyLine",
    "checklistProgress", "askAvaToPlanIt", "avaPlanNextQuestion"]) {
    assert.match(week, new RegExp(`"${key}"`), key);
  }
  assert.match(week, /<AvaOnly>/, "Ask Ava to plan it falls back while Ava is off");
  assert.match(sheet, /\{shownWeek && <GoalWeek week=\{shownWeek\}/);
  assert.match(source("records/AreaScreen.jsx"), /week=\{/);
  assert.deepEqual([text.en.thisWeekHeading, text.zh.thisWeekHeading], ["This week", "本周"]);
});

test("a Learning goal's sheet opened from the Goals screen loads Learn's week and shows the same This week", () => {
  const sheet = source("records/GoalsScreen.jsx");
  const body = sheet.slice(sheet.indexOf("export function GoalSheet"), sheet.indexOf("\n}\n", sheet.indexOf("export function GoalSheet")));
  assert.match(body, /goal\?\.domain !== "learning"/, "only for a Learning goal");
  assert.match(body, /api\(`\/api\/areas\/learning\?\$\{new URLSearchParams\(\{ date: today \}\)\}`\)/);
  assert.match(body, /\.catch\(\(\) => live && setLoaded\(null\)\)/, "an unreachable service leaves the section out");
  assert.match(body, /const shownWeek = week \?\? loaded;/);
  const screen = sheet.slice(sheet.indexOf("export function GoalsScreen"));
  assert.match(screen, /<GoalSheet [\s\S]*?onOpenTask=\{onOpenTask\} onAskAva=\{onAskAva\} \/>/);
  assert.match(source("App.jsx"), /<GoalsScreen [\s\S]*?onOpenTask=\{\(item\) => openTask\(item\)\} onAskAva=\{askAva\}/);
});
