import assert from "node:assert/strict";
import test from "node:test";
import { noticeText, talkLog } from "../src/talk/notices.js";
import { interfaceText } from "./interfaceText.mjs";

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);

test("Ava asks whether a meal moves for good or on one day, naming the meal and its new times", () => {
  assert.equal(noticeText({ kind: "clarify-meal-scope", values: { meal: "lunch", start: "12:30", end: "13:30" } }, t, "en"),
    'avaClarifyMealScope {"meal":"mealLunch","range":"12:30–13:30"}');
});

test("Ava asks whether a repeating task's change reaches the repeat from today on, naming the task and day", () => {
  assert.equal(noticeText({ kind: "clarify-repeat-scope", values: { title: "Stretch", date: "2026-10-03" } }, t, "en"),
    'avaClarifyRepeatScope {"title":"Stretch","date":"Saturday 3 October"}');
});

/** A message about an issue as the local service returns it. */
function notice(kind, values, createdAt = "2026-10-03T08:00:00+00:00") {
  return { id: `notice-${kind}`, date: "2026-10-03", kind, agentKey: "learning", values, createdAt, readAt: null };
}

test("a task that keeps slipping is worded with its latest reports", () => {
  assert.equal(noticeText(notice("slipping", { taskTitle: "Read", unfinished: 2, latest: 3 }), t, "en"),
    'avaNoticeSlipping {"title":"Read","unfinished":2,"latest":3}');
});

test("a length that is off is worded by why it looks off, with its minutes as the interface reads them", () => {
  assert.equal(noticeText(notice("length-off", { taskTitle: "Report", minutes: 90, partial: 3, reported: 4, reason: "unfinished" }), t, "en"),
    'avaNoticeLengthUnfinished {"title":"Report","minutes":"1 h 30 min","partial":3,"reported":4}');
  assert.equal(noticeText(notice("length-off", { taskTitle: "Report", minutes: 45, changes: 2, reason: "changing" }), t, "zh"),
    'avaNoticeLengthChanging {"title":"Report","minutes":"45 分钟","changes":2}');
});

test("a day that won't fit and a full day on low energy are worded with the day's minutes", () => {
  assert.equal(noticeText(notice("day-wont-fit", { count: 3, taskMinutes: 720, freeMinutes: 660 }), t, "en"),
    'avaNoticeDayWontFit {"count":3,"taskMinutes":"12 h","freeMinutes":"11 h"}');
  assert.equal(noticeText(notice("low-energy-full", { energy: 2, taskMinutes: 480, freeMinutes: 660 }), t, "en"),
    'avaNoticeLowEnergyFull {"energy":2,"taskMinutes":"8 h","freeMinutes":"11 h"}');
});

test("a day with no free time left says so, with the time its tasks without a time need", () => {
  assert.equal(noticeText(notice("day-wont-fit", { count: 2, taskMinutes: 75, freeMinutes: 0 }), t, "en"),
    'avaNoticeDayWontFitNoTime {"taskMinutes":"1 h 15 min"}');
  assert.equal(interfaceText().en.avaNoticeDayWontFitNoTime, "No free time is left today for tasks without a time ({taskMinutes}).");
  assert.ok(interfaceText().zh.avaNoticeDayWontFitNoTime);
});

test("a Learning goal due for review and a stalled Project goal are worded with the goal and its days", () => {
  assert.equal(noticeText(notice("due-for-review", { goalId: "goal_1", goalTitle: "French", days: 4 }), t, "en"),
    'avaNoticeDueForReview {"title":"French","days":4}');
  assert.equal(noticeText(notice("stalled", { goalId: "goal_2", goalTitle: "Shed", days: 3 }), t, "zh", (title) => `《${title}》`),
    'avaNoticeStalled {"title":"《Shed》","days":3}');
  const text = interfaceText();
  const fill = (template, values) => template.replace(/\{(\w+)\}/g, (match, name) => values[name]);
  assert.deepEqual([fill(text.en.avaNoticeDueForReview, { title: "French", days: 4 }), fill(text.zh.avaNoticeStalled, { title: "Shed", days: 3 }),
    fill(text.en.avaNoticeLowEnergyFull, { energy: 2, taskMinutes: "8 h", freeMinutes: "11 h" })], [
    "“French” is due for review: nothing toward it has been done for 4 days. A short session today keeps it fresh.",
    "“Shed”停滞了：已经 3 天没有任何进展。添加它的下一步，或者暂停这个目标。",
    "You reported your energy at 2/5 today, and your tasks without a time need 8 h of the 11 h you have free. Ask me for a lighter day."]);
});

test("a task title in a message can be shown in the interface language", () => {
  assert.equal(noticeText(notice("slipping", { taskTitle: "Read", unfinished: 2, latest: 3 }), t, "zh", (title) => `《${title}》`),
    'avaNoticeSlipping {"title":"《Read》","unfinished":2,"latest":3}');
});

test("an agent's doubt about a change says what its records show, with lengths as the interface reads them", () => {
  assert.equal(noticeText(notice("doubt-usual-time", { taskTitle: "Read", usualStart: "08:30", requested: "21:00", done: 4 }), t, "en"),
    'avaDoubtUsualTime {"title":"Read","usual":"08:30","requested":"21:00","done":4}');
  assert.equal(noticeText(notice("doubt-too-short", { taskTitle: "Read", requested: 30, partial: 3, partialMinutes: 30, doneMinutes: 60 }), t, "en"),
    'avaDoubtTooShort {"title":"Read","requested":"30 min","partial":3,"partialMinutes":"30 min","doneMinutes":"1 h"}');
  assert.equal(noticeText(notice("doubt-too-short", { taskTitle: "Read", requested: 30, partial: 3, partialMinutes: 30, doneMinutes: null }), t, "en"),
    'avaDoubtTooShortNoDone {"title":"Read","requested":"30 min","partial":3,"partialMinutes":"30 min","doneMinutes":null}');
  // A finishing length no longer than the one left partly done says nothing more, so it isn't named.
  assert.match(noticeText(notice("doubt-too-short", { taskTitle: "Read", requested: 30, partial: 3, partialMinutes: 60, doneMinutes: 60 }), t, "en"),
    /^avaDoubtTooShortNoDone /);
});

test("an agent asks which task a change means, by the time or length asked for, or among the tasks that fit", () => {
  assert.equal(noticeText(notice("clarify-task", { requested: "15:00", minutes: null }), t, "en"), 'avaClarifyTaskTime {"time":"15:00"}');
  assert.equal(noticeText(notice("clarify-task", { requested: null, minutes: 30 }), t, "en"), 'avaClarifyTaskLength {"minutes":"30 min"}');
  const lookup = (key, values) => (key === "listSeparator" ? "; " : values ? `${key} ${JSON.stringify(values)}` : key);
  assert.equal(noticeText(notice("clarify-which", { tasks: [{ title: "Walk", start: "08:00" }, { title: "Walk", start: null }] }), lookup, "en"),
    'avaClarifyWhich {"tasks":"avaClarifyTaskAt {\\"title\\":\\"Walk\\",\\"time\\":\\"08:00\\"}; avaClarifyTaskUntimed {\\"title\\":\\"Walk\\"}"}');
});

test("a kind of message this interface doesn't know is left out", () => {
  assert.equal(noticeText(notice("later-kind", {}), t, "en"), "");
  assert.deepEqual(talkLog([], [notice("later-kind", {})]), []);
});

test("Ava's log puts its messages about issues among the conversation by when each was made", () => {
  const messages = [
    { id: "m1", role: "user", content: "Hi", created_at: "2026-10-03T07:00:00+00:00" },
    { id: "m2", role: "assistant", content: "Hello", created_at: "2026-10-03T09:00:00+00:00" },
    { id: "local-1", role: "user", content: "Sending" },
  ];
  const log = talkLog(messages, [notice("slipping", { taskTitle: "Read", unfinished: 2, latest: 3 })]);
  assert.deepEqual(log.map((entry) => entry.message?.id || entry.notice.id), ["m1", "notice-slipping", "m2", "local-1"]);
});

test("Ava's log marks where the conversation turns to another day, and nowhere else", () => {
  const turn = (id, role, topicDate, minute) => ({ id, role, content: id, topicDate, created_at: `2026-10-03T08:${minute}:00+00:00` });
  const messages = [turn("old", "user", null, "00"), turn("a1", "user", "2026-10-03", "01"), turn("a2", "assistant", "2026-10-03", "02"),
    turn("b1", "user", "2026-10-01", "03"), turn("b2", "assistant", "2026-10-01", "04"),
    { id: "local-1", role: "user", content: "Sending", topicDate: "2026-10-03" }];

  const log = talkLog(messages, []);

  assert.deepEqual(log.map((entry) => entry.topic || entry.message.id),
    ["old", "a1", "a2", "2026-10-01", "b1", "b2", "2026-10-03", "local-1"]);
});
