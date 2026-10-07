import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { AS_IS, CHOICE_KEYS, UNDO_SECONDS, choiceOptions, chosenStatuses, firstChoices, savedKey } from "../src/records/catchUp.js";
import { proposalView } from "../src/talk/proposal.js";
import { noticeText } from "../src/talk/notices.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const say = (language) => (key, values = {}) => text[language][key].replace(/\{(\w+)\}/g, (_, name) => values[name]);

// A day as the service lists it to catch up on, with the status Ava read for some of them.
const TASKS = [
  { id: "review", title: "Review", start: "09:00", status: "done", noReply: false, to: null },
  { id: "email", title: "Email", start: "10:00", status: "planned", noReply: false, to: "done" },
  { id: "gym", title: "Gym", start: "11:00", status: "planned", noReply: true, to: null },
  { id: "read", title: "Read", start: null, status: "partial", noReply: false, to: "skipped" },
];

test("a task with a status shows it chosen and can change it; one without starts as it is, or as Ava read it", () => {
  assert.deepEqual(firstChoices(TASKS), { review: "done", email: "done", gym: AS_IS, read: "skipped" });
  assert.deepEqual(choiceOptions(TASKS[0]), ["done", "partial", "skipped"]);
  assert.deepEqual(choiceOptions(TASKS[2]), [AS_IS, "done", "partial", "skipped"]);
  // One set of status words everywhere: the sheet's choices are the status controls' own.
  assert.deepEqual(Object.values(CHOICE_KEYS).map((key) => say("en")(key)), ["As is", "Done", "Partly done", "Skipped"]);
  assert.deepEqual(Object.values(CHOICE_KEYS).map((key) => say("zh")(key)), ["保持不变", "已完成", "部分完成", "已跳过"]);
  assert.deepEqual(Object.keys(CHOICE_KEYS).slice(1).map((status) => CHOICE_KEYS[status]), ["done", "partial", "skipped"]);
});

test("one save sends only the tasks whose status changes, mixed statuses together", () => {
  const choices = { ...firstChoices(TASKS), review: "partial", gym: "skipped" };
  assert.deepEqual(chosenStatuses(TASKS, choices), { review: "partial", email: "done", gym: "skipped", read: "skipped" });
  assert.deepEqual(chosenStatuses(TASKS, { review: "done", email: AS_IS, gym: AS_IS, read: "partial" }), {});
});

test("the save's notice counts the tasks updated and offers Undo for a few seconds", () => {
  assert.equal(say("en")(savedKey(1)), "1 task updated");
  assert.equal(say("en")(savedKey(3), { count: 3 }), "3 tasks updated");
  assert.equal(say("zh")(savedKey(3), { count: 3 }), "已更新 3 项任务");
  assert.ok(UNDO_SECONDS >= 5 && UNDO_SECONDS <= 10);
  const workspace = readFileSync(new URL("../src/workspace.js", import.meta.url), "utf8");
  assert.match(workspace, /api\("\/api\/catch-up", \{ method: "POST"/);
  assert.match(workspace, /api\("\/api\/catch-up\/undo", \{ method: "POST" \}\)/);
  assert.match(source("App.jsx"), /notice\.action/);
});

test("Ava's catch-up card reads every task with its status now and the one proposed", () => {
  const view = proposalView({ actionType: "catch_up", payload: { date: "2026-10-05", tasks: TASKS } }, []);
  assert.deepEqual(view, { kind: "catchUp", date: "2026-10-05", tasks: TASKS });
  assert.equal(say("en")("proposalCatchUpTitle", { when: "on Mon 5 Oct" }), "Catch up on Mon 5 Oct");
  // On Confirm, the card sends the choices the user made on it.
  assert.match(source("talk/ProposalCard.jsx"), /statuses: chosenStatuses\(view\.tasks, choices\)/);
});

test("a partly done Learning task's offer to continue next session is worded", () => {
  assert.equal(noticeText({ kind: "continue-offer", values: { taskTitle: "Study chapter 4" } }, say("en"), "en"),
    "“Study chapter 4” is partly done, with items still unticked. Continue it next session?");
});

test("Catch up is on Today, Tasks and Ava's panel, and never in the menu bar", () => {
  assert.match(source("today/TodayScreen.jsx"), /onClick=\{onCatchUp\}/);
  assert.match(source("records/TasksScreen.jsx"), /onClick=\{onCatchUp\}/);
  assert.match(source("talk/TalkPanel.jsx"), /send\(t\("catchUpPrompt"\)\)/);
  assert.doesNotMatch(source("menubar/MenuBarPanel.jsx"), /catchUp|CatchUp|catch-up/);
  assert.equal((source("App.jsx").match(/onCatchUp=\{/g) || []).length, 2, "the one sheet opens from Today and Tasks");
  assert.equal(say("en")("catchUpPrompt"), "Catch up");
});

test("the Guide's Today card names Catch up within the shared word limit", async () => {
  const { cardWords } = await import("../src/guide/guideCards.js");
  const { WORD_LIMIT } = await import("../src/wording.js");
  const guide = JSON.parse(readFileSync(new URL("../src/guide/guide.json", import.meta.url), "utf8"));
  const card = guide.sections.flatMap((section) => section.cards).find((entry) => entry.id === "today");
  assert.match(card.do, /Catch up/);
  assert.ok(cardWords(card) <= WORD_LIMIT, `${cardWords(card)} words`);
});

test("yesterday's notice opens Ava's catch-up card for yesterday, sent at once", () => {
  assert.match(source("today/TodayScreen.jsx"), /onAskAva\(t\("catchUpYesterdayPrompt"\), true\)/);
  assert.equal(say("en")("catchUpYesterdayPrompt"), "Catch up on yesterday");
  assert.equal(say("zh")("catchUpYesterdayPrompt"), "补记昨天");
  assert.equal(text.en.yesterdayPrompt, undefined, "the sentence begun about one task is gone");
  // Confirming yesterday's card from Today keeps Today on show, refreshed, so its notice of yesterday updates.
  const workspace = readFileSync(new URL("../src/workspace.js", import.meta.url), "utf8");
  assert.match(workspace, /const shown = changedDate < today && day\.date === today \? today : changedDate;/);
  assert.match(workspace, /catch_up: "noticeCaughtUp"/);
  assert.equal(say("en")("noticeCaughtUp"), "Statuses updated.");
});
