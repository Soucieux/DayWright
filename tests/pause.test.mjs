import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { noReplyOf, yesterdayLines } from "../src/records/timeTaken.js";
import { FOLLOW_PARTS, planFollowThrough } from "../src/ui/progress.js";
import { changeLine, proposalView, shownChange } from "../src/talk/proposal.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);

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
  assert.match(readFileSync(new URL("../src/bench.css", import.meta.url), "utf8"), /\.dw-follow-dayPaused \{/);
});

test("the next day's notice says when the day was paused, beside the tasks it left not done", () => {
  const paused = yesterdayLines({ date: "2026-10-06", pausedAt: "14:10", tasks: [{ id: "a", title: "Review", reason: "dayPaused" }] }, t);
  assert.equal(paused.paused, 'yesterdayPausedAt {"time":"14:10"}');
  assert.equal(paused.tasks[0], 'yesterdayTaskLine {"title":"Review","reason":"yesterdayDayPaused"}');
  const times = yesterdayLines({ date: "2026-10-06", pausedAt: "09:20", tasks: [{ id: "b", title: "Inbox", reason: "checkTime" }] }, t);
  assert.equal(times.paused, null, "the paused line goes with the tasks it explains");
  assert.equal(text.en.yesterdayPausedAt, "You paused at {time}");
});

test("Today pauses and resumes from its header, saying since when", () => {
  const today = source("today/TodayScreen.jsx");
  assert.match(today, /day\.pausedSince\s*\?/);
  assert.match(today, /onClick=\{onResume\}/);
  assert.match(today, /onClick=\{onPause\}/);
  assert.match(today, /t\("pausedSinceChip", \{ time: day\.pausedSince \}\)/);
  assert.deepEqual([text.en.pauseDayAction, text.en.resumeDayAction, text.en.pausedSinceChip], ["Pause", "Resume", "Paused since {time}"]);
  const workspace = source("workspace.js");
  assert.match(workspace, /api\("\/api\/day\/pause", \{ method: "POST" \}\)/);
  assert.match(workspace, /api\("\/api\/day\/resume", \{ method: "POST" \}\)/);
});

test("the menu bar's panel pauses and resumes too, and its title says since when", () => {
  const panel = source("menubar/MenuBarPanel.jsx");
  assert.match(panel, /now\?\.pausedSince \?/);
  assert.match(panel, /`\/api\/day\/\$\{now\?\.pausedSince \? "resume" : "pause"\}`/);
  assert.match(panel, /askShell\("refresh"\)/);
});

test("Ava's pause and resume cards read what they change", () => {
  assert.deepEqual(proposalView({ actionType: "pause_day", payload: { date: "2026-10-07", since: null } }, []),
    { kind: "pause", date: "2026-10-07", since: null });
  assert.deepEqual(proposalView({ actionType: "resume_day", payload: { date: "2026-10-07", since: "14:10" } }, []),
    { kind: "resume", date: "2026-10-07", since: "14:10" });
  for (const key of ["proposalPauseTitle", "proposalPauseLine", "proposalPauseNote", "proposalResumeTitle", "proposalResumeLine",
    "noticeDayPaused", "noticeDayResumed"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
});

test("Ava's edit card says a task left on a day that ended paused was Not done · paused, not no reply", () => {
  const edit = (paused) => proposalView({ actionType: "edit_item", payload: { date: "2026-10-07", itemId: "item_1", title: "Review",
    changes: { status: "partial" }, before: { status: "planned" }, ...(paused ? { dayPaused: true } : {}) } }, []);
  assert.equal(edit(true).dayPaused, true);
  assert.equal("dayPaused" in edit(false), false);
  const before = (view, today) => shownChange(view.changes[0], view, today).from;
  assert.deepEqual([before(edit(true), "2026-10-08"), before(edit(false), "2026-10-08"), before(edit(true), "2026-10-07")],
    ["dayPaused", "noReply", "planned"]);
  assert.match(changeLine(shownChange(edit(true).changes[0], edit(true), "2026-10-08"), t, "en", []), /"from":"dayPaused"/);
  assert.match(source("talk/ProposalCard.jsx"), /changeLine\(shownChange\(change, view, today\)/);
});

test("the Guide's Today card says how to pause and resume, and that paused time counts nowhere", () => {
  const guide = JSON.parse(readFileSync(new URL("../src/guide/guide.json", import.meta.url), "utf8"));
  const card = guide.sections.flatMap((section) => section.cards).find((entry) => entry.id === "today");
  assert.equal(card.do, "set your energy, report statuses or Catch up; Pause and Resume; the menu bar shows now and next.");
  assert.equal(card.rule, "only you mark Done; paused time counts nowhere; at 22:00 what's left reads Not done · no reply, or · paused.");
  assert.ok(card.words.includes("pause"));
});
