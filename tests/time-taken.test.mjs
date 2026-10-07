import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import { timeColumn } from "../src/records/taskDraft.js";
import { CHECK_TIME_FACTOR, noReplyOf, spentMinutes, timeTaken, yesterdayLines } from "../src/records/timeTaken.js";
import { changeLine, proposalView } from "../src/talk/proposal.js";
import { noticeText } from "../src/talk/notices.js";
import { dayRows } from "../src/today/dayRows.js";
import { FOLLOW_PARTS, planFollowThrough } from "../src/ui/progress.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const say = (key, values = {}) => text.en[key].replace(/\{(\w+)\}/g, (_, name) => values[name]);
const tagged = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);

test("a task's time taken is its recorded stretch; one over twice its length is a time to check until confirmed", () => {
  const review = { duration_minutes: 60, actualStart: "14:00", actualEnd: "15:10", timeConfirmed: false };
  assert.deepEqual(timeTaken(review), { start: "14:00", end: "15:10", minutes: 70, toCheck: false });
  assert.equal(timeTaken({ duration_minutes: 60 }), null);
  assert.equal(CHECK_TIME_FACTOR, 2);
  const long = { duration_minutes: 60, actualStart: "09:00", actualEnd: "12:20", timeConfirmed: false };
  assert.equal(timeTaken(long).toCheck, true);
  assert.equal(timeTaken({ ...long, timeConfirmed: true }).toCheck, false);
  // A plan's entry reads its task's time.
  assert.equal(timeTaken({ duration_minutes: 60, source: review }).minutes, 70);
});

test("time spent counts every status's time taken, a planned length for a task reported before times were kept, and no time to check", () => {
  assert.equal(spentMinutes({ completion_status: "skipped", duration_minutes: 60, actualStart: "14:00", actualEnd: "14:20" }), 20);
  assert.equal(spentMinutes({ completion_status: "done", duration_minutes: 45 }), 45);
  assert.equal(spentMinutes({ completion_status: "skipped", duration_minutes: 45 }), 0);
  assert.equal(spentMinutes({ completion_status: "planned", duration_minutes: 45 }), 0);
  assert.equal(spentMinutes({ completion_status: "done", duration_minutes: 60, actualStart: "09:00", actualEnd: "12:20" }), 0);
  assert.match(source("today/TodayScreen.jsx"), /spentMinutes\(row\)/, "Today's chip and balance count time spent");
});

test("a schedule row shows when it started and the time it took once its status set them", () => {
  const row = { start_time: "14:00", duration_minutes: 60, source: { actualStart: "14:05", actualEnd: "15:15" } };
  assert.deepEqual(timeColumn(row, "en"), { start: "14:05", length: "1 h 10 min", taken: true });
  assert.deepEqual(timeColumn({ start_time: "14:00", duration_minutes: 60 }, "en"), { start: "14:00", length: "1 h" });
});

test("the Untimed list keeps the order its tasks were made in", () => {
  const item = (id, created) => ({ id, title: id, start_time: null, duration_minutes: 30, acceptance: "accepted",
    completion_status: "planned", createdAt: created });
  const { untimed } = dayRows({ confirmedVariantId: null, entries: [], dayItems: [item("b", "2026-10-07T09:00:00+00:00"),
    item("a", "2026-10-07T08:00:00+00:00")] });
  assert.deepEqual(untimed.map((row) => row.id), ["a", "b"]);
  assert.equal(text.en.untimed, "Untimed");
  assert.equal(text.zh.untimed, "未定时");
});

test("a task left without a status once its day's 22:00 passed reads Not done · no reply, with its own glyph", () => {
  assert.equal(noReplyOf({ noReply: true }), true);
  assert.equal(noReplyOf({ source: { noReply: true } }), true);
  assert.equal(noReplyOf({ completion_status: "planned" }), false);
  assert.equal(text.en.noReply, "Not done · no reply");
  assert.ok(existsSync(new URL("../design/icons/status-noreply.svg", import.meta.url)));
  const control = source("ui/StatusControl.jsx");
  assert.match(control, /noReply/);
  assert.doesNotMatch(control, /nothing here infers one from the time of day/, "its account says DayWright marks no reply");
  for (const path of ["today/TodayScreen.jsx", "calendar/DayPanel.jsx", "records/TaskSheet.jsx", "records/TasksScreen.jsx", "records/AreaCards.jsx"]) {
    assert.match(source(path), /noReply=\{/, `${path} passes no reply`);
  }
});

test("follow-through counts unanswered entries apart from skipped, and today's still to do as not yet reported", () => {
  assert.deepEqual(FOLLOW_PARTS, ["done", "partial", "moved", "skipped", "noReply", "unreported"]);
  const counts = planFollowThrough([{ completion_status: "planned", source: { noReply: true } },
    { completion_status: "planned", source: {} }, { completion_status: "skipped", source: {} }]);
  assert.deepEqual([counts.noReply, counts.unreported, counts.skipped], [1, 1, 1]);
  assert.match(source("ui/ProgressGraphs.jsx"), /noReply: "noReply"/);
});

test("yesterday's notice says what each task needs, to fix through Ava", () => {
  const notice = { date: "2026-10-06", tasks: [{ id: "a", title: "Journal", reason: "noReply" },
    { id: "b", title: "Review", reason: "stopped" }, { id: "c", title: "Write", reason: "checkTime" }] };
  assert.deepEqual(yesterdayLines(notice, say), {
    title: say("yesterdayNoticeTitle", { count: 3 }),
    tasks: ["Journal: " + say("yesterdayNoReply"), "Review: " + say("yesterdayStopped"), "Write: " + say("yesterdayCheckTime")],
  });
  assert.match(source("today/TodayScreen.jsx"), /<YesterdayNotice /);
});

test("Ava's agents word the usual-length offer and the signals of tasks often skipped or left unanswered", () => {
  assert.equal(noticeText({ kind: "usual-length", values: { taskTitle: "Review", usualMinutes: 75, setMinutes: 60 } }, tagged, "en"),
    'avaNoticeUsualLength {"title":"Review","usual":"1 h 15 min","set":"1 h"}');
  assert.equal(noticeText({ kind: "often-skipped", values: { taskTitle: "Stretch", count: 2, scheduled: 3 } }, tagged, "en"),
    'areaNoteOftenSkipped {"title":"Stretch","count":2,"scheduled":3}');
  assert.equal(noticeText({ kind: "often-unanswered", values: { taskTitle: "Journal", count: 2, scheduled: 3 } }, tagged, "en"),
    'areaNoteOftenUnanswered {"title":"Journal","count":2,"scheduled":3}');
  assert.match(source("talk/TalkPanel.jsx"), /notice\.proposal\?\.status === "pending"/, "the offer shows its card until decided");
});

test("the usual-length card and an edit to the time a past task took read what changes", () => {
  const usual = proposalView({ actionType: "usual_length", payload: { date: "2026-10-08", itemIds: ["a", "b"], durationMinutes: 75,
    title: "Review", fromMinutes: 60 } }, []);
  assert.deepEqual(usual, { kind: "usual", date: "2026-10-08", title: "Review", from: 60, to: 75, days: 2 });
  assert.equal(changeLine({ field: "actualTime", from: { start: "09:00", end: "10:00" }, to: { start: "09:00", end: "11:00" } },
    say, "en", []), say("proposalFieldLine", { field: say("fieldActualTime"), from: "09:00–10:00", to: "09:00–11:00" }));
  assert.equal(changeLine({ field: "timeConfirmed", from: false, to: true }, say, "en", []), say("proposalTimeConfirmed"));
});

test("a length an agent learned from the time a task took says so", () => {
  assert.match(source("records/TaskSheet.jsx"), /estimateBasis === "taken"/);
  assert.match(text.en.estimatedFromTaken, /\{agent\}/);
});
