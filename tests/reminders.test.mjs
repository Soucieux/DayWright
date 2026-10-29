import assert from "node:assert/strict";
import test from "node:test";
import { talkLog } from "../src/talk/notices.js";
import { REMINDERS_SHOWN, reminderLine } from "../src/today/reminders.js";
import { guideCard, interfaceText, say, source } from "./interfaceText.mjs";

const text = interfaceText();
const TODAY = "2026-10-14";

/** A reminder as the local service gives Today one. */
function reminder(kind, values = {}, since = TODAY, agentKey = "learning") {
  return { id: `notice-${kind}`, kind, agentKey, values, since, createdAt: `${TODAY}T08:00:00+00:00` };
}

test("each kind of reminder has its short form and its one action, in English and Chinese", () => {
  const cases = [
    [reminder("slipping", { taskTitle: "Read" }), "“Read” keeps slipping", "“Read”一再推迟", "seeTasks"],
    [reminder("length-off", { taskTitle: "Report", minutes: 90 }), "“Report” runs other than planned", "“Report”的用时与计划不符", "changeLength"],
    [reminder("day-wont-fit", { count: 3 }, TODAY, "orchestrator"), "Today's tasks don't fit the day", "今天的任务排不下", "comparePlans"],
    [reminder("low-energy", { energy: 2 }, TODAY, "life"), "Low energy today", "今天精力不足", null],
    [reminder("low-energy-full", { energy: 2 }, TODAY, "orchestrator"), "Low energy, and a full day", "精力不足，今天又排得很满", null],
    [reminder("due-for-review", { goalId: "goal", goalTitle: "Spanish to B1" }), "“Spanish to B1” is due for review", "“Spanish to B1”该复习了", "planSession"],
    [reminder("stalled", { goalId: "goal", goalTitle: "Piano" }, TODAY, "project"), "“Piano” has stalled", "“Piano”停滞了", "addStep"],
  ];
  for (const [given, english, chinese, action] of cases) {
    assert.deepEqual([reminderLine(given, TODAY, say("en")).text, reminderLine(given, TODAY, say("zh")).text], [english, chinese], given.kind);
    assert.equal(reminderLine(given, TODAY, say("en")).action, action, given.kind);
  }
  assert.equal(reminderLine(reminder("continue-offer"), TODAY, say("en")), null, "an offer is never a reminder");
});

test("a reminder's age is the days since its issue first came up", () => {
  assert.equal(reminderLine(reminder("slipping", { taskTitle: "Read" }), TODAY, say("en")).since, "today");
  assert.equal(reminderLine(reminder("slipping", { taskTitle: "Read" }, "2026-10-13"), TODAY, say("en")).since, "for 1 day");
  assert.equal(reminderLine(reminder("slipping", { taskTitle: "Read" }, "2026-10-11"), TODAY, say("en")).since, "for 3 days");
  assert.equal(reminderLine(reminder("slipping", { taskTitle: "Read" }, "2026-10-11"), TODAY, say("zh")).since, "已 3 天");
});

test("Today's notice box holds yesterday as it was, a divider only with both, then Reminders · N with three shown", () => {
  assert.equal(REMINDERS_SHOWN, 3);
  const screen = source("today/TodayScreen.jsx");
  const box = screen.slice(screen.indexOf("function TodayNotices"), screen.indexOf("\n}\n", screen.indexOf("function TodayNotices")));
  assert.match(box, /\{yesterday && reminders\.length > 0 && <hr className="dw-notices-divider" \/>\}/);
  assert.match(box, /t\("remindersTitle", \{ count: reminders\.length \}\)/);
  assert.match(box, /\(open \? reminders : reminders\.slice\(0, REMINDERS_SHOWN\)\)/);
  assert.match(box, /t\("remindersMore", \{ count: reminders\.length - REMINDERS_SHOWN \}\)/);
  assert.match(box, /onDismissReminders\(reminders\.map\(\(shown\) => shown\.id\)\)/, "the group's Dismiss acts on its reminders only");
  assert.match(box, /onDismissReminders\(\[item\.id\]\)/, "a reminder's on that reminder only");
  assert.match(screen, /\{\(day\.yesterdayNotice \|\| reminders\.length > 0 \|\| day\.holidayReminder\) && <TodayNotices/,
    "no box with none of them");
  assert.match(screen, /reminderLine\(item, day\.date, t\)/);
});

test("Ava's chat leaves reminders out and puts offers arriving together in one group", () => {
  /** A time on 14 Oct 2026, `minute` minutes past 08:00 UTC. */
  const at = (minute) => `2026-10-14T08:${String(minute).padStart(2, "0")}:00+00:00`;
  const notices = [
    { id: "slip", kind: "slipping", group: "reminder", agentKey: "learning", values: { taskTitle: "Read" }, createdAt: at(1) },
    { id: "first", kind: "continue-offer", group: "offer", agentKey: "learning", values: { taskTitle: "Lesson 4" }, createdAt: at(2) },
    { id: "second", kind: "link-offer", group: "offer", agentKey: "learning", values: { taskTitle: "Lesson 4", count: 2 }, createdAt: at(3) },
    { id: "third", kind: "usual-length", group: "offer", agentKey: "work", values: { taskTitle: "Report" }, createdAt: at(9) },
  ];
  const messages = [{ id: "answer", role: "assistant", content: "Done.", created_at: at(5), topicDate: TODAY }];
  const log = talkLog(messages, notices);
  assert.deepEqual(log.map((entry) => entry.offers ? entry.offers.map((offer) => offer.id) : entry.key),
    [["first", "second"], "answer", ["third"]]);
  const panel = source("talk/TalkPanel.jsx");
  assert.match(panel, /t\("avaOffersGroup", \{ count: offers\.length \}\)/);
  assert.match(panel, /notice\.proposal\?\.status === "pending"/, "an undecided card stays open");
  assert.match(panel, /<TalkNotice key=\{notice\.id\} notice=\{notice\} folded \/>/, "a decided one folds");
});

test("the Guide's Today card says to handle reminders there, and Ava's that offers come to her and reminders to Today", () => {
  assert.match(guideCard("today").do, /handle reminders/);
  assert.ok(guideCard("today").words.includes("reminders"));
  assert.equal(guideCard("ava").rule, "nothing changes until you press Confirm; the agents' offers come here, and their reminders go to Today.");
  assert.ok(guideCard("ava").words.includes("offers"));
});

test("with Ava off, yesterday's line saying she needs a model reads icon, words, then Open Settings, never one over another", () => {
  const css = source("bench.css");
  assert.match(css, /\.dw-yesterday \.dw-needs-model \{ display: grid; grid-template-columns: 16px minmax\(0, 1fr\) auto; align-items: start; max-width: 34em; \}/);
  assert.match(css, /\.dw-yesterday \.dw-needs-model > \.dw-icon \{ margin-top: 2px; \}/);
  // On a phone the line keeps to the box's width, and Open Settings takes its own line under the words.
  assert.match(css, /@media \(max-width: 640px\) \{\s*\.dw-yesterday \.dw-actions \{ flex: 1 1 calc\(100% - 28px\); min-width: 0; \}\s*\.dw-yesterday \.dw-needs-model \{ grid-template-columns: 16px minmax\(0, 1fr\); \}\s*\.dw-yesterday \.dw-needs-model \.dw-link \{ grid-column: 2; justify-self: start; \}/);
});

test("every new word has its Chinese", () => {
  for (const key of ["remindersTitle", "remindersMore", "remindersDismissAll", "reminderDismissNamed", "reminderPlanPrompt",
    "reminderSeeTasks", "reminderChangeLength", "reminderComparePlans", "reminderPlanSession", "reminderAddStep", "avaOffersGroup"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
});
