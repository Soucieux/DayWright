import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { daysText, entryLine, missingFields, neededText, ruleWhat, shortDay } from "../src/settings/memory.js";
import { noticeText } from "../src/talk/notices.js";
import { proposalView } from "../src/talk/proposal.js";
import { interfaceText } from "./interfaceText.mjs";

const text = interfaceText();
const say = (language) => (key, values = {}) => {
  assert.ok(text[language][key], `${language} ${key}`);
  return text[language][key].replace(/\{(\w+)\}/g, (match, name) => String(values[name] ?? match));
};
const en = say("en");
const zh = say("zh");
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");

const KEEP_FREE = { kind: "rule", ruleKind: "keep-free", start: "18:00", end: "19:00", days: [0, 1, 2, 3, 4], endsOn: "2026-12-31",
  saidOn: "2026-10-09" };
const KEEP_OFF = { kind: "rule", ruleKind: "keep-off", area: "work", days: [5, 6], saidOn: "2026-10-09" };
const GYM = { kind: "rule", ruleKind: "keep-off", task: "Gym", days: [0, 2, 4], saidOn: "2026-10-09" };
const FINISH = { kind: "rule", ruleKind: "finish-by", latest: "18:00", days: [0, 1, 2, 3, 4, 5, 6], saidOn: "2026-10-09" };
const NOTE = { kind: "note", area: "learning", wording: "I study best in the morning", saidOn: "2026-10-09" };

test("an entry reads as the service names it: kind, what, days and end", () => {
  assert.equal(entryLine(KEEP_FREE, en, "en"), "Rule · Keep free · 18:00–19:00 · Mon–Fri · until 31 Dec");
  assert.equal(entryLine(KEEP_OFF, en, "en"), "Rule · Keep off · Work · Sat–Sun");
  assert.equal(entryLine(GYM, en, "en"), "Rule · Keep off · “Gym” · Mon, Wed, Fri");
  assert.equal(entryLine(FINISH, en, "en"), "Rule · Finish by · 18:00 · Every day");
  assert.equal(entryLine(NOTE, en, "en"), "Note · Learn · I study best in the morning");
  assert.equal(entryLine({ ...NOTE, area: "general" }, en, "en"), "Note · General · I study best in the morning");
});

test("in Chinese too", () => {
  assert.equal(entryLine(KEEP_FREE, zh, "zh"), "规则 · 留空 · 18:00–19:00 · 周一至周五 · 至12月31日");
  assert.equal(entryLine(KEEP_OFF, zh, "zh"), "规则 · 不安排 · 工作 · 周六至周日");
  assert.equal(daysText([0, 2, 4], zh, "zh"), "周一、周三、周五");
  assert.equal(entryLine(NOTE, zh, "zh"), "笔记 · 学习 · I study best in the morning");
  assert.equal(shortDay("2026-12-31", "zh"), "12月31日");
});

test("a rule names what it still needs, so a card can make a note a rule once filled", () => {
  assert.deepEqual(missingFields({ ruleKind: "keep-free", days: [] }), ["start", "end", "days"]);
  assert.deepEqual(missingFields({ ruleKind: "keep-free", start: "19:00", end: "18:00", days: [0] }), ["end"]);
  assert.deepEqual(missingFields({ ruleKind: "keep-off", task: "  ", days: [1] }), ["area"]);
  assert.deepEqual(missingFields({ ruleKind: "finish-by", latest: "17:30", days: [4] }), []);
  assert.equal(neededText(["start", "end", "days"], en, "en"), "a start time, an end time and its days");
  assert.equal(neededText(["latest"], zh, "zh"), "最晚结束时间");
  assert.equal(ruleWhat(FINISH, en), "18:00");
});

test("Ava's memory cards read what each keeps, changes or deletes", () => {
  const remember = proposalView({ actionType: "remember", payload: { entry: NOTE, outcome: "add", missing: ["start", "end", "days"],
    rule: "keep-free", ruleFields: {}, offered: true } }, []);
  assert.deepEqual([remember.kind, remember.rule, remember.missing, remember.offered], ["remember", "keep-free", ["start", "end", "days"], true]);
  const change = proposalView({ actionType: "change_memory", payload: { changes: [{ op: "delete", before: KEEP_OFF }] } }, []);
  assert.deepEqual([change.kind, change.changes.length], ["memoryChange", 1]);
  const forget = proposalView({ actionType: "forget_memory", payload: { topic: "gym", entries: [GYM], lines: [{ id: 1, day: "2026-10-01",
    text: "Gym renews in March" }] } }, []);
  assert.deepEqual([forget.kind, forget.topic, forget.entries.length, forget.lines.length], ["memoryForget", "gym", 1, 1]);
  const review = proposalView({ actionType: "review_memory", payload: { entries: [{ entry: NOTE, day: "2026-10-01" }] } }, []);
  assert.deepEqual([review.kind, review.entries.length], ["memoryReview", 1]);
});

test("the card offering what past conversations held is Ava's message", () => {
  assert.equal(noticeText({ kind: "memory-review", values: { count: 2 } }, en, "en"),
    "From our earlier conversations, 2 things you may want me to remember.");
  assert.equal(noticeText({ kind: "memory-review", values: { count: 1 } }, zh, "zh"), "从我们之前的对话中，有 1 条你可能希望我记住。");
});

test("a remember card names Ava, says a rule kept as a note, and lets the rule be filled before Confirm", () => {
  const card = source("talk/ProposalCard.jsx");
  assert.match(card, /\["agent", t\("proposalRememberAva", \{ agent: t\("navTalk"\) \}\)\]/);
  assert.match(card, /proposalRememberAsNote/);
  assert.match(card, /<EntryFields entry=\{rule\} onChange=\{setRule\} \/>/);
  assert.match(card, /memory: rule/);
  assert.match(card, /\|\| ruleUnfinished\}/, "an unfinished rule can't be confirmed");
  assert.match(card, /kept: \[\.\.\.kept\]/, "a card of offers sends the ones left ticked");
});

test("Settings › Memory sits below Models: rules in a table, notes by area, past ones, each with Edit and a two-step Delete", () => {
  const sheet = source("settings/SettingsSheet.jsx");
  assert.ok(sheet.indexOf("dw-settings-models") < sheet.indexOf("<MemorySection"), "Memory comes after Models");
  const section = source("settings/MemorySection.jsx");
  for (const column of ["memoryColumnKind", "memoryColumnWhat", "memoryColumnDays", "memoryColumnEnds", "memoryColumnFrom"]) {
    assert.match(section, new RegExp(`<th scope="col">\\{t\\("${column}"\\)\\}</th>`), column);
  }
  assert.ok(section.indexOf("memoryColumnKind") < section.indexOf("memoryColumnWhat"));
  assert.ok(section.indexOf("memoryColumnDays") < section.indexOf("memoryColumnEnds"));
  assert.match(section, /MEMORY_AREAS\.filter\(\(area\) => memory\.notes\.some/, "notes are grouped by their area tag");
  assert.match(section, /memoryPastHeading/);
  assert.match(section, /editable=\{false\}/, "a past entry can only be deleted");
  assert.match(section, /stepTwoOfTwo/, "Delete takes two steps");
  assert.match(section, /memoryDeleteAction/);
  assert.doesNotMatch(section, /isReady|NeedsModel/, "Memory works without the model");
});

test("Settings › Memory shows how you work from your records, all time and the last 30 days, read-only", () => {
  const section = source("settings/MemorySection.jsx");
  assert.ok(section.indexOf("memoryNotesHeading") < section.indexOf("memoryRecordsHeading"), "after the notes");
  assert.ok(section.indexOf("memoryRecordsHeading") < section.indexOf("memoryPastHeading"), "before the past ones");
  assert.match(section, /\[\["allTime", "memoryRecordsAllTime"\], \["lastThirty", "memoryRecordsLastThirty"\]\]/);
  const records = section.slice(section.indexOf("memoryRecordsHeading"), section.indexOf("memoryPastHeading"));
  assert.doesNotMatch(records, /EntryActions|onSave|onDelete|<button/, "nothing in it is edited or deleted");
  assert.match(records, /memory\.records\[key\]\.map/);
  assert.equal(en("memoryRecordsHeading"), "From your records");
  assert.equal(zh("memoryRecordsHeading"), "来自你的记录");
  assert.equal(en("memoryRecordsLastThirty"), "Last 30 days");
});

test("a task placed against a rule names the rule it breaks on its sheet", () => {
  assert.match(source("records/TaskSheet.jsx"), /\(task\?\.ruleBreaks \|\| \[\]\)\.map\(\(rule\) =>/);
  assert.equal(en("taskBreaksRule", { rule: "Rule · Keep free · 18:00–19:00 · Mon–Fri" }),
    "Against your rule: Rule · Keep free · 18:00–19:00 · Mon–Fri. It's kept as you placed it; plans keep to the rule.");
});

test("every memory text exists in both languages, and plans word their rules in Chinese", () => {
  for (const key of ["settingsMemory", "memoryLead", "memoryEmpty", "memoryRulesHeading", "memoryNotesHeading", "memoryPastHeading",
    "memoryPastLead", "memoryColumnKind", "memoryColumnWhat", "memoryColumnDays", "memoryColumnEnds", "memoryColumnFrom",
    "memoryColumnActions", "memoryRule", "memoryNote", "ruleKeepFree", "ruleKeepOff", "ruleFinishBy", "memoryEveryDay", "memoryUntil",
    "memoryNoEnd", "memorySaid", "memoryEnded", "areaGeneral", "memoryFieldWording", "memoryWordCount", "memoryFieldEnd",
    "memoryFieldLatest", "memoryFieldArea", "memoryChooseArea", "memoryAreaTask", "memoryFieldTask", "memoryFieldDays",
    "memoryFieldEnds", "memorySave", "memoryEditNamed", "memoryDeleteNamed", "memoryDeleteEllipsis", "memoryDeleteQuestion",
    "memoryDeleteAction", "memoryDeleteNote", "needFieldStart", "needFieldEnd", "needFieldLatest", "needFieldDays", "needFieldArea",
    "proposalRememberTitle", "proposalRememberOfferTitle", "proposalMemoryChangeTitle", "proposalRememberAva",
    "proposalRememberAsNote", "proposalMakeRule", "proposalKeepNote", "proposalRuleNeeds", "proposalRememberSettings",
    "proposalMemoryEnd", "proposalMemoryDelete", "proposalForgetTitle", "proposalForgetLine", "proposalForgetNote",
    "proposalMemoryReviewTitle", "proposalMemoryReviewNote", "avaNoticeMemoryReview", "avaNoticeMemoryReviewOne", "taskBreaksRule",
    "memoryRecordsHeading", "memoryRecordsLead", "memoryRecordsAllTime", "memoryRecordsLastThirty"]) {
    assert.ok(text.en[key] && text.zh[key], key);
  }
  assert.equal(zh("planRuleFree", { start: "18:00", end: "19:00" }), "按你的规则留出 18:00–19:00。");
  assert.equal(zh("planRuleFinish", { time: "17:00" }), "按你的规则在 17:00 前结束。");
  assert.equal(zh("planRuleOff", { tasks: "“健身”" }), "按你的规则，这一天不安排“健身”。");
});
