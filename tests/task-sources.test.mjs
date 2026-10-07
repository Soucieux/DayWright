import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { linkedNames, namesList } from "../src/records/learningTasks.js";
import { noticeText } from "../src/talk/notices.js";
import { proposalView } from "../src/talk/proposal.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);

test("a Learn task names every Library item it uses, its checklist's first, as the Library names them", () => {
  const view = { sourceId: "s1", sourceTitle: "Lesson 4.md · 0123456789ab",
    references: [{ id: "s2", title: "Grammar notes" }, { id: "s3", title: "Verb tables" }] };
  assert.deepEqual(linkedNames(view), ["Lesson 4.md", "Grammar notes", "Verb tables"]);
  assert.deepEqual(linkedNames({ sourceId: null, sourceTitle: null, references: [] }), []);
});

test("names read as a list in either language", () => {
  assert.equal(namesList(["Grammar notes"], "en"), "Grammar notes");
  assert.equal(namesList(["Grammar notes", "Lesson 4.md"], "en"), "Grammar notes and Lesson 4.md");
  assert.equal(namesList(["A", "B", "C"], "en"), "A, B and C");
  assert.equal(namesList(["A", "B", "C"], "zh"), "A、B和C");
});

test("moving a Learn task that uses the Library out of Learn is refused before Save, naming what it uses", () => {
  const sheet = source("records/TaskSheet.jsx");
  assert.match(sheet, /const leaving = used\.length > 0 && draft\.domain !== "learning"/);
  assert.match(sheet, /const canSave = backendConnected && !saving && !clash && !leaving/);
  assert.equal(text.en.taskStaysInLearnOne, "It uses {sources} from your Library, so it stays in Learn. Unlink it to move it.");
  assert.equal(text.en.taskStaysInLearnMany, "It uses {sources} from your Library, so it stays in Learn. Unlink them to move it.");
  assert.ok(text.zh.taskStaysInLearnOne && text.zh.taskStaysInLearnMany);
});

test("a Learn task's details link and unlink Library items, its checklist's own included; other tasks offer none", () => {
  const briefing = source("records/Checklist.jsx");
  assert.match(briefing, /<TaskLibrary /);
  assert.match(briefing, /\$\{base\}\/sources/);
  assert.match(briefing, /t\("taskLibraryChecklistFrom"\)[\s\S]{0,300}changeLink\(learned\.sourceId, false\)/,
    "the checklist's own item is named once, on its line, with Unlink");
  assert.doesNotMatch(briefing, /taskSourceLabel/);
  assert.match(briefing, /\{learned\.passId && \(\s*<div className="dw-learning-effort">/,
    "a checklist kept after its item is unlinked keeps its effort, which the plans still read");
  assert.equal(text.en.taskSourceLabel, undefined);
  assert.equal(text.en.taskLibraryTitle, "References");
  assert.match(source("records/TaskSheet.jsx"), /task && task\.domain === "learning" && \(\s*<LearningBriefing/);
  for (const key of ["taskLibraryTitle", "taskLibraryChecklistFrom", "taskLibraryLinkAction", "taskLibraryUnlinkAction",
    "taskLibraryNone", "taskLibraryPast"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
});

test("Ava's link card names the task and each Library item it links or unlinks", () => {
  const linking = proposalView({ actionType: "link_sources", payload: { date: "2026-10-07", title: "Lesson 4", link: true,
    proposedBy: "learning", sources: [{ id: "s1", title: "Grammar notes" }] } }, []);
  assert.deepEqual(linking, { kind: "link", date: "2026-10-07", title: "Lesson 4", link: true, suggested: true,
    sources: [{ id: "s1", title: "Grammar notes" }] });
  assert.equal(proposalView({ actionType: "link_sources", payload: { date: "2026-10-07", title: "Lesson 4", link: false,
    proposedBy: "orchestrator", sources: [] } }, []).suggested, false);
});

test("Ava's folder card lists each file checked with its verdict, ready ones ticked", () => {
  const files = [{ path: "a.md", title: "A", verdict: "ready", reason: null, ticked: true },
    { path: "scan.pdf", title: "scan", verdict: "unreadable", reason: "No text to read: it may be scanned pages.", ticked: false }];
  assert.deepEqual(proposalView({ actionType: "folder_check", payload: { folderId: "f1", title: "Course", files, modelChecked: false } }, []),
    { kind: "folderCheck", date: null, title: "Course", files, modelChecked: false });
  assert.match(source("talk/ProposalCard.jsx"), /ticked: \[\.\.\.ticks\]/);
});

test("while a folder's files are checked, the Library is read again for its progress, then the day for Ava's card", () => {
  const workspace = source("workspace.js");
  assert.match(workspace, /const checking = library\.folders\.some\(\(folder\) => folder\.checking\)/);
  assert.match(workspace, /window\.setTimeout\(loadLibrary, FOLDER_CHECK_POLL_MS\)/);
  assert.match(workspace, /if \(checkedRef\.current && !checking\) loadDay\(day\.date, false\)/);
  assert.match(source("library/SourceList.jsx"),
    /folder\.checking\.total == null \? t\("folderCheckingStart"\) : t\("folderChecking", folder\.checking\)/);
  assert.equal(text.en.folderCheckingStart, "Checking files…");
});

test("confirming a folder's check or a link card reloads the Library and the day, with its own notice", () => {
  assert.match(source("workspace.js"), /if \(actionType === "folder_check" \|\| actionType === "link_sources"\) \{\s*await Promise\.all\(\[loadDay\(day\.date, false\), loadLibrary\(\)\]\);\s*showNotice\(actionType === "folder_check" \? "noticeFolderChecked" : "noticeLinksChanged"\)/);
  assert.equal(text.en.noticeFolderChecked, "Library updated from the folder's check.");
  assert.equal(text.en.noticeLinksChanged, "Task's Library links updated.");
  assert.ok(text.zh.noticeFolderChecked && text.zh.noticeLinksChanged);
});

test("Ava's notices say what she suggests linking and what a folder's check found", () => {
  assert.equal(noticeText({ kind: "link-offer", values: { taskTitle: "Lesson 4", count: 2 } }, t, "en"),
    'avaNoticeLinkOffer {"title":"Lesson 4","count":2}');
  assert.equal(noticeText({ kind: "folder-check", values: { title: "Course", ready: 1, unreadable: 2, notStudy: 1 } }, t, "en"),
    'avaNoticeFolderCheck {"title":"Course","ready":1,"unreadable":2,"notStudy":1}');
  for (const key of ["avaNoticeLinkOffer", "avaNoticeFolderCheck", "proposalLinkTitle", "proposalUnlinkTitle",
    "proposalLinkLine", "proposalUnlinkLine", "proposalFolderCheckTitle", "proposalFolderCheckNoModel", "folderCheckReady",
    "folderCheckUnreadable", "folderCheckNotStudy", "folderChecking"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
});
