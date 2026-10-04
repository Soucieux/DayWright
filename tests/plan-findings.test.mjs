import assert from "node:assert/strict";
import test from "node:test";
import { findingText, findingsFor, votesText } from "../src/plans/findings.js";
import { planName } from "../src/plans/planName.js";
import { planChanges } from "../src/today/planChanges.js";

/** A stored task with only the fields a plan's changes read. */
function task(id, start, minutes = 60, extra = {}) {
  return { id, title: id, domain: "project", start_time: start, duration_minutes: minutes, acceptance: "accepted", ...extra };
}

/** A set plan's entry for a task. */
function entry(source, start, minutes = 60) {
  return { id: `entry-${source}`, title: source, domain: "project", source_item_id: source, start_time: start, duration_minutes: minutes };
}

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (values ? `${key} ${JSON.stringify(values)}` : key);
const same = (value) => value;

test("a plan's changes name the tasks it placed, moved or resized and the ones it kept", () => {
  const tasks = [task("notes", null, 45), task("guide", null, 60), task("standup", "10:00", 30), task("moved", "14:00"),
    task("later", "16:00"), task("waiting", null, 30, { acceptance: "pending" })];
  const entries = [entry("notes", "08:00", 45), entry("guide", "08:45", 45), entry("standup", "10:00", 30), entry("moved", "15:00")];
  const { changed, kept, missing } = planChanges(entries, tasks);
  assert.deepEqual(changed.map(({ task: source, placed, moved, resized }) => [source.id, placed, moved, resized]),
    [["notes", true, false, false], ["guide", true, false, true], ["moved", false, true, false]]);
  assert.deepEqual(kept.map((row) => row.id), ["entry-standup"]);
  assert.deepEqual(missing.map((row) => row.id), ["later"]);
});

test("the findings behind a task come from every area agent's run in the plan's route", () => {
  const route = [
    { agentKey: "orchestrator", phase: "dispatch", findings: [] },
    { agentKey: "project", phase: "assessment", findings: [
      { agent: "project", kind: "shorten", taskTitle: "guide", domain: "project" },
      { agent: "project", kind: "time", taskTitle: "guide", domain: "project" },
      { agent: "project", kind: "keep", taskTitle: "guide", domain: "project" },
      { agent: "project", kind: "new", taskTitle: "notes", domain: "project" }] },
    { agentKey: "summary", phase: "summary" },
  ];
  assert.deepEqual(findingsFor(route, "guide", "project", ["shorten", "time"]).map((finding) => [finding.agent, finding.kind]),
    [["project", "shorten"], ["project", "time"]]);
  assert.deepEqual(findingsFor(undefined, "guide", "project", ["shorten"]), []);
});

test("a finding is worded from its own numbers, with its first step and lengths in the interface language", () => {
  const shorten = findingText({ kind: "shorten", taskTitle: "Guide", partial: 1, skipped: 2, reported: 4,
    fromMinutes: 60, toMinutes: 45, firstStep: "Outline" }, t, "en", same);
  assert.match(shorten, /^findingShorten .*"task":"Guide".*"from":"1 h".*"to":"45 min"/);
  assert.match(shorten, /findingFirstStep \{"step":"Outline"\}$/);
  assert.match(findingText({ kind: "hold", taskTitle: "Walk", reason: "yours", firstStep: "" }, t, "en", same),
    /^findingHold .*"reason":"holdYours"[^}]*\}$/);
  assert.match(findingText({ kind: "time", taskTitle: "Notes", preferredStart: "08:30", done: 3 }, t, "zh", same),
    /^findingTime .*"time":"08:30"/);
  assert.equal(findingText({ kind: "area-life", date: "2026-10-01", energy: 2, sleep: null, habitDone: 0, habitReports: 0, lighter: true }, t, "en", same),
    'findingCheckIn {"date":"2026-10-01"}findingEnergy {"energy":2}findingLighter');
  assert.equal(findingText({ kind: "something-new" }, t, "en", same), "");
});

test("an area agent's votes name its plans best first, and an agent that didn't vote says nothing", () => {
  const votes = [{ kind: "focused", reason: "focus" }, { kind: "rhythm", reason: "usual-times" }];
  const plans = [planName({ slug: "focused" }, t, same), planName({ slug: "rhythm" }, t, same)].join(t("listSeparator"));
  assert.equal(votesText(votes, t, same), t("agentVotes", { plans }));
  assert.equal(votesText(undefined, t, same), "");
  assert.equal(votesText([], t, same), "");
});

test("a finding says when a task has lately been slipping or improving, and nothing when it is steady", () => {
  const keep = { kind: "keep", taskTitle: "Notes", done: 3, reported: 4, minutes: 45 };
  assert.match(findingText({ ...keep, trend: "slipping" }, t, "en", same), /findingTrendSlipping$/);
  assert.match(findingText({ ...keep, trend: "improving" }, t, "en", same), /findingTrendImproving$/);
  assert.doesNotMatch(findingText({ ...keep, trend: "steady" }, t, "en", same), /findingTrend/);
});
