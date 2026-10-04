import assert from "node:assert/strict";
import test from "node:test";
import { noticeText, talkLog } from "../src/talk/notices.js";

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);

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
