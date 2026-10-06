import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { checklistMark, continueRequest, fromSourceRequest, movedIndex, offersContinue, pastTickRequest, startCheckLine, suggestsDone }
  from "../src/records/learningTasks.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
const t = (key, values = {}) => text.en[key].replace(/\{(\w+)\}/g, (_, name) => values[name]);
const ENTRIES = [{ key: "a", sourceId: "a", title: "Basics", sections: [] },
  { key: "b", sourceId: "b", title: "Consuming HTTP Services", sections: ["Setup", "Interceptors"] },
  { key: "c", sourceId: "c", title: "Routing", sections: ["Guards"] }];
const entry = (id, title, fields = {}) => ({ id, title, heading: title, addedBy: "source", pageState: "", tickedAt: null, tickedOn: null,
  ...fields });
const CHECKLIST = [entry("1", "Setup", { tickedAt: "2026-10-06T10:00:00" }), entry("2", "Interceptors"),
  entry("3", "Notes", { addedBy: "you", heading: null })];
const LEARNED = { checklist: CHECKLIST, allTicked: false, startCheck: "", startCheckedAt: null };

test("From a source sends the ticked files in their listed order, their day, how they spread, the goal and the pass", () => {
  const ticked = new Set(["c", "a"]);
  assert.deepEqual(fromSourceRequest(ENTRIES, ticked, { date: "2026-10-07", spread: "oneADay", goal: "", newGoal: "", fresh: false }),
    { sourceIds: ["a", "c"], date: "2026-10-07", oneADay: true, goal: null, fresh: false });
  assert.deepEqual(fromSourceRequest(ENTRIES, new Set(["b"]), { date: "2026-10-07", spread: "oneADay", goal: "goal_1", newGoal: "", fresh: true }),
    { sourceIds: ["b"], date: "2026-10-07", oneADay: false, goal: { goalId: "goal_1" }, fresh: true }, "one file has nothing to spread");
  assert.deepEqual(fromSourceRequest(ENTRIES, ticked, { date: "2026-10-07", spread: "allOn", goal: "new", newGoal: "  Angular ", fresh: false }).goal,
    { title: "Angular" });
});

test("a checklist item is marked as the user's, or as new or gone in its source, in that source's words", () => {
  assert.equal(checklistMark(entry("1", "x", { addedBy: "you" }), "website"), "checklistYours");
  assert.equal(checklistMark(entry("1", "x", { pageState: "new" }), "website"), "checklistNewOnPage");
  assert.equal(checklistMark(entry("1", "x", { pageState: "gone" }), "website"), "checklistGoneFromPage");
  assert.equal(checklistMark(entry("1", "x", { pageState: "new" }), "folder"), "checklistNewInFile");
  assert.equal(checklistMark(entry("1", "x", { pageState: "gone" }), "file"), "checklistGoneFromFile");
  assert.equal(checklistMark(entry("1", "x"), "folder"), null);
});

test("Alt+↑ and Alt+↓ move an item one place, never past either end", () => {
  assert.equal(movedIndex(CHECKLIST, "2", -1), 0);
  assert.equal(movedIndex(CHECKLIST, "2", 1), 2);
  assert.equal(movedIndex(CHECKLIST, "1", -1), null);
  assert.equal(movedIndex(CHECKLIST, "3", 1), null);
});

test("every item ticked suggests Done until it is done or set aside; partly done offers the next session", () => {
  assert.equal(suggestsDone("planned", { ...LEARNED, allTicked: true }, false), true);
  assert.equal(suggestsDone("done", { ...LEARNED, allTicked: true }, false), false);
  assert.equal(suggestsDone("planned", { ...LEARNED, allTicked: true }, true), false, "Not now sets it aside");
  assert.equal(suggestsDone("planned", LEARNED, false), false);
  assert.equal(offersContinue("partial", LEARNED), true);
  assert.equal(offersContinue("planned", LEARNED), false);
  assert.equal(offersContinue("partial", { ...LEARNED, checklist: [entry("1", "x", { tickedAt: "t" }), entry("2", "y", { pageState: "gone" })] }),
    false, "nothing left to study");
});

test("Ava is asked in the words she reads: continue a task, or tick or untick an item on a past day", () => {
  assert.equal(continueRequest("Consuming HTTP Services", t), "Continue “Consuming HTTP Services” next session");
  assert.equal(pastTickRequest("HTTP", CHECKLIST, t), "Tick “Interceptors” in “HTTP”");
  assert.equal(pastTickRequest("HTTP", [entry("1", "Setup", { tickedAt: "t" })], t), "Untick “Setup” in “HTTP”");
  assert.equal(text.zh.avaContinueRequest, "下次继续“{title}”");
  assert.equal(text.zh.avaTickRequest, "勾选“{title}”中的“{item}”");
  assert.equal(text.zh.avaUntickRequest, "取消勾选“{title}”中的“{item}”");
});

test("a website's start check says when it updated the task, or that the site couldn't be reached", () => {
  assert.deepEqual(startCheckLine({ startCheck: "updated", startCheckedAt: "2026-10-06T10:05:30" }), { key: "websiteUpdatedAt", time: "10:05" });
  assert.deepEqual(startCheckLine({ startCheck: "unreachable", startCheckedAt: "2026-10-06T10:05:30" }), { key: "websiteCheckFailed" });
  assert.equal(startCheckLine({ startCheck: "unchanged", startCheckedAt: "2026-10-06T10:05:30" }), null);
  assert.equal(startCheckLine({ startCheck: "", startCheckedAt: null }), null);
});

test("From a source lives in the task form, not New goal, and adds tasks by the learning-task route", () => {
  const form = source("records/TaskSheet.jsx");
  assert.match(form, /<FromSourceSheet /);
  assert.match(form, /t\("fromSourceAction"\)/);
  assert.doesNotMatch(source("records/GoalsScreen.jsx"), /FromSource|fromSource|topic/i);
  const sheet = source("records/FromSourceSheet.jsx");
  assert.match(sheet, /api\("\/api\/learning-tasks", \{ method: "POST"/);
  assert.match(sheet, /fromSourceRequest\(/);
  for (const key of ["spreadAllOn", "spreadOneADay", "groupLabel", "startFreshLabel", "entryProgress"]) {
    assert.match(sheet, new RegExp(`t\\("${key}"`), key);
  }
});

test("the checklist is real checkboxes, one per line, edited, reordered and ticked through its own routes", () => {
  const list = source("records/Checklist.jsx");
  assert.match(list, /type="checkbox"/);
  assert.doesNotMatch(list, /<textarea|- \[ \]/, "never a text box or Markdown");
  for (const route of ["/checklist`", "/tick`", "/move`"]) assert.ok(list.includes(route), route);
  assert.match(list, /event\.altKey && \(event\.key === "ArrowUp" \|\| event\.key === "ArrowDown"\)/);
  assert.match(list, /draggable/);
  const both = list + source("records/TaskSheet.jsx");
  for (const key of ["checklistAddAction", "checklistProgress", "checklistPastNote", "doneSuggestion", "continueNextSession"]) {
    assert.match(both, new RegExp(`t\\("${key}"`), key);
  }
});

test("the task's briefing looks its website up as it opens on its day, and a page that changed refreshes the day", () => {
  const briefing = source("records/Checklist.jsx");
  assert.match(briefing, /\/briefing-opened`/);
  assert.match(briefing, /answer\.startCheck === "updated"\) onUpdated\(\)/, "the sheet's length follows the page's new estimate");
  assert.match(source("App.jsx"), /<TaskSheet [^>]*onUpdated=\{refreshKnowledge\}/);
});

test("a length estimated from the task's source says so", () => {
  assert.match(source("records/TaskSheet.jsx"), /task\.estimateBasis === "source" \? t\("estimatedFromSource"\)/);
  assert.equal(text.en.estimatedFromSource, "Estimated from what its source holds. Give your own in Edit, or ask Ava.");
  assert.ok(text.zh.estimatedFromSource);
});

test("Subjects name each goal's next task to study; Ava's cards say what a follow-up carries and what a tick changes", () => {
  const cards = source("records/AreaCards.jsx");
  const subjects = cards.slice(cards.indexOf("export function SubjectsCard("));
  assert.match(subjects, /t\("nextStudyLine"/);
  assert.match(subjects, /onAskAva\(t\("avaPlanNextQuestion", \{ goal: demoText\(subject\.title\) \}\)\)/);
  assert.doesNotMatch(cards, /topic/i);
  assert.match(source("talk/ProposalCard.jsx"), /t\("proposalContinueLine"/);
  assert.match(source("talk/ProposalCard.jsx"), /t\(view\.done \? "proposalTick" : "proposalUntick"/);
  assert.equal(text.en.avaPlanNextQuestion, "What should I study next in “{goal}”?");
});

test("every learning-task text exists in both languages, and v4.5's goal topics are gone", () => {
  for (const key of ["fromSourceTitle", "fromSourceNote", "fromSourceOffer", "entrySectionsCount", "entryOneSection", "entryNoSections",
    "entryProgress", "spreadAllOn", "spreadOneADay", "groupLabel", "groupNone", "groupNew", "newGoalNameLabel", "startFreshLabel",
    "startFreshNote", "addTasksAction", "addOneTaskAction", "madeTasks", "madeOneTask", "checklistHeading", "checklistProgress",
    "checklistAddAction", "checklistNewItemLabel", "checklistRenameLabel", "checklistRemoveLabel", "checklistMoveLabel", "checklistMoved",
    "checklistYours", "checklistNewOnPage", "checklistGoneFromPage", "checklistNewInFile", "checklistGoneFromFile", "checklistTickedAt",
    "checklistPastNote", "checklistAskAva", "checklistEmpty", "doneSuggestion", "markDoneAction", "notNowAction", "continueNextSession",
    "avaContinueRequest", "avaTickRequest", "avaUntickRequest", "websiteUpdatedAt", "websiteCheckFailed", "taskEffortLabel",
    "nextStudyLine", "allTasksDone", "askAvaToPlanIt", "avaPlanNextQuestion", "proposalContinueLine", "proposalTick", "proposalUntick",
    "originalNotFound", "locateOriginalAction"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
  assert.equal(text.en.checklistProgress, "{done} of {total} sections done");
  assert.equal(text.en.doneSuggestion, "All sections ticked: mark it Done?");
  assert.equal(text.en.websiteUpdatedAt, "Updated from the website at {time}");
  assert.equal(text.en.websiteCheckFailed, "Couldn't check the website");
  assert.equal(text.en.checklistPastNote, "To change it, ask Ava.");
  assert.equal(text.en.originalNotFound, "Original not found");
  for (const key of ["proposalTopicLine", "goalTopicsLine", "topicsHeading", "nextTopicLine", "askAvaToPlanTopic", "avaPlanTopicQuestion",
    "allTopicsStudied", "entryTopicsCount", "makeGoalsAction", "madeGoals", "siteTooLittle"]) {
    assert.equal(text.en[key] ?? text.zh[key], undefined, key);
  }
  for (const words of Object.values(text.en)) assert.doesNotMatch(words, /\btopics?\b/i, words);
});

test("no folder or path is assumed in the learning-task interface", () => {
  for (const path of ["records/FromSourceSheet.jsx", "records/Checklist.jsx", "records/learningTasks.js", "records/TaskSheet.jsx"]) {
    assert.doesNotMatch(source(path), /\/Users\/|~\/Documents|\/Volumes\/|Knowledge Transfer|Professional Quality|observatory/i, path);
  }
});
