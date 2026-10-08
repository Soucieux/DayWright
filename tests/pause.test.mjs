import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { proposalView } from "../src/talk/proposal.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

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
