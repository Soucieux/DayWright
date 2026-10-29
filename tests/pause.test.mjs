import assert from "node:assert/strict";
import test from "node:test";
import { noReplyOf, yesterdayLines } from "../src/records/timeTaken.js";
import { FOLLOW_PARTS, planFollowThrough } from "../src/ui/progress.js";
import { changeLine, proposalView, shownChange } from "../src/talk/proposal.js";
import { guideCard, interfaceText, keyText as t, source } from "./interfaceText.mjs";

const text = interfaceText();

test("a task left without a status reads no reply, or paused on a day that ended paused", () => {
  assert.equal(noReplyOf({ noReply: true }), "noReply");
  assert.equal(noReplyOf({ dayPaused: true }), "dayPaused");
  assert.equal(noReplyOf({ source: { dayPaused: true } }), "dayPaused");
  assert.equal(noReplyOf({ status: "planned" }), false);
  assert.deepEqual([text.en.dayPaused, text.zh.dayPaused], ["Not done · paused", "未完成 · 已暂停"]);
  const control = source("ui/StatusControl.jsx");
  assert.match(control, /const reading = noReply === true \? NO_REPLY : noReply/);
  assert.match(source("records/CatchUpList.jsx"), /noReply=\{noReplyOf\(task\)\}/);
});

test("the follow-through bar keeps a paused day's tasks apart from no reply", () => {
  assert.deepEqual(FOLLOW_PARTS, ["done", "partial", "moved", "skipped", "noReply", "dayPaused", "unreported"]);
  const counts = planFollowThrough([{ completion_status: "planned", source: { dayPaused: true } },
    { completion_status: "planned", source: { noReply: true } }]);
  assert.deepEqual([counts.dayPaused, counts.noReply], [1, 1]);
  assert.match(source("bench.css"), /\.dw-follow-dayPaused \{/);
});

test("the next day's notice says when the day was paused and asks Ava to check times when that is all it holds", () => {
  const paused = yesterdayLines({ date: "2026-10-06", pausedAt: "14:10", tasks: [{ id: "a", title: "Review", reason: "dayPaused" }] }, t);
  assert.equal(paused.paused, 'yesterdayPausedAt {"time":"14:10"}');
  assert.equal(paused.tasks[0], 'yesterdayTaskLine {"title":"Review","reason":"yesterdayDayPaused"}');
  assert.equal(paused.onlyTimes, false);
  const times = yesterdayLines({ date: "2026-10-06", pausedAt: "09:20", tasks: [{ id: "b", title: "Inbox", reason: "checkTime" }] }, t);
  assert.equal(times.paused, null, "the paused line goes with the tasks it explains");
  assert.equal(times.onlyTimes, true);
  assert.equal(text.en.yesterdayPausedAt, "You paused at {time}");
  assert.deepEqual([text.en.checkTimesAction, text.en.checkTimesPrompt], ["Check times with Ava", "Check yesterday's times"]);
  assert.match(source("today/TodayScreen.jsx"), /onlyTimes \? t\("checkTimesPrompt"\) : t\("catchUpYesterdayPrompt"\)/);
});

test("Today pauses and resumes from its header, saying since when, and marks a task stopped at its limit", () => {
  const today = source("today/TodayScreen.jsx");
  assert.match(today, /day\.pausedSince\s*\?/);
  assert.match(today, /onClick=\{onResume\}/);
  assert.match(today, /onClick=\{onPause\}/);
  assert.match(today, /t\("pausedSinceChip", \{ time: day\.pausedSince \}\)/);
  assert.equal((today.match(/\{limited && !paused && <span className="dw-row-note"><Icon name="alert" size=\{16\} \/>\{t\("limitStoppedNote"\)\}/g) || []).length, 1,
    "once, in the row both the schedule and the untimed list show");
  assert.equal(text.en.limitStoppedNote, "Stopped at its limit · set its status");
  assert.deepEqual([text.en.pauseDayAction, text.en.resumeDayAction, text.en.pausedSinceChip], ["Pause", "Resume", "Paused since {time}"]);
  const workspace = source("workspace.js");
  assert.match(workspace, /api\("\/api\/day\/pause", \{ method: "POST" \}\)/);
  assert.match(workspace, /api\("\/api\/day\/resume", \{ method: "POST" \}\)/);
});

test("the menu bar pauses and resumes too, through the app's own routes, saying since when", () => {
  const shell = source("../src-tauri/src/menubar.rs");
  assert.match(shell, /"pause" => Some\(\("POST", "\/api\/day\/pause"\.to_string\(\), None\)\)/);
  assert.match(shell, /"resume" => Some\(\("POST", "\/api\/day\/resume"\.to_string\(\), None\)\)/);
  const menu = source("../backend/app/menubar.py");
  assert.match(menu, /items \+= \[_line\(words\["paused"\]\.format\(time=now\["pausedSince"\]\)\), _action\("resume", words\["resume"\]\)\]/);
});

test("Ava's pause, resume and check-times cards read what they change", () => {
  assert.deepEqual(proposalView({ actionType: "pause_day", payload: { date: "2026-10-07", since: null } }, []),
    { kind: "pause", date: "2026-10-07", since: null });
  assert.deepEqual(proposalView({ actionType: "resume_day", payload: { date: "2026-10-07", since: "14:10" } }, []),
    { kind: "resume", date: "2026-10-07", since: "14:10" });
  const tasks = [{ itemId: "a", title: "Inbox", start: "09:00", end: "10:00", minutes: 60, setMinutes: 30 }];
  assert.deepEqual(proposalView({ actionType: "check_times", payload: { date: "2026-10-06", tasks } }, []),
    { kind: "checkTimes", date: "2026-10-06", tasks });
  const card = source("talk/ProposalCard.jsx");
  assert.match(card, /times: checkedTimes\(view\.tasks, checks\)/);
  for (const key of ["proposalPauseTitle", "proposalPauseLine", "proposalPauseNote", "proposalResumeTitle", "proposalResumeLine",
    "proposalCheckTimesTitle", "proposalCheckTimesNote", "checkTimeRight", "checkTimeChange", "checkTimeMinutes", "noticeDayPaused",
    "noticeDayResumed", "noticeTimesChecked"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
});

test("Ava's edit card says a task left on a day that ended paused was Not done · paused, not no reply", () => {
  /** Ava's card marking a past task partly done, on a day paused when `paused`. */
  const edit = (paused) => proposalView({ actionType: "edit_item", payload: { date: "2026-10-07", itemId: "item_1", title: "Review",
    changes: { status: "partial" }, before: { status: "planned" }, ...(paused ? { dayPaused: true } : {}) } }, []);
  assert.equal(edit(true).dayPaused, true);
  assert.equal("dayPaused" in edit(false), false);
  /** What a card's first change shows it was before, read on `today`. */
  const before = (view, today) => shownChange(view.changes[0], view, today).from;
  assert.deepEqual([before(edit(true), "2026-10-08"), before(edit(false), "2026-10-08"), before(edit(true), "2026-10-07")],
    ["dayPaused", "noReply", "planned"]);
  assert.match(changeLine(shownChange(edit(true).changes[0], edit(true), "2026-10-08"), t, "en", []), /"from":"dayPaused"/);
  assert.match(source("talk/ProposalCard.jsx"), /changeLine\(shownChange\(change, view, today\)/);
});

test("the Guide's Today card says how to pause and resume, and that paused time counts nowhere", () => {
  const card = guideCard("today");
  assert.equal(card.do, "set energy, report statuses or Catch up; handle reminders; Pause, Resume; the menu bar shows now and next.");
  assert.equal(card.rule, "only you mark Done; paused time counts nowhere; at day's end what's left reads Not done · no reply, or · paused.");
  assert.ok(card.words.includes("pause"));
});
