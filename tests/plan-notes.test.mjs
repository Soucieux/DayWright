import assert from "node:assert/strict";
import test from "node:test";
import { PLAN_TYPES, planName } from "../src/plans/planName.js";
import { planNotes } from "../src/plans/planNotes.js";

test("every kind of plan, Balanced first, has a name, a one-line description and when it is offered", () => {
  assert.deepEqual(PLAN_TYPES.map((type) => type.slug),
    ["balanced", "focused", "gentle", "early", "quickwins", "easiest", "rhythm", "spacious"]);
  for (const type of PLAN_TYPES) {
    assert.equal(planName({ slug: type.slug }, (key) => key, (value) => value), type.name);
    assert.match(type.tagline, /^planTagline/);
    assert.match(type.when, /^planWhen/);
  }
});

/** An interface text lookup that shows which message was asked for and with what. */
const t = (key, values) => (key === "listSeparator" ? "、" : `${key} ${JSON.stringify(values)}`);
const same = (value) => value;

/** A plan's sentence as the planner stores it. */
function note(key, values, text) {
  return { key, values, text };
}

const focused = {
  slug: "focused",
  rationale: "Suggested because … Keeps …",
  notes: [
    note("planWhyFocus", { count: 2 }, "Suggested because you have 2 work, project, and learning tasks to keep together."),
    note("planDoesFocus", { tasks: ["Report", "Build"], start: "13:00", end: "15:00" },
      "Keeps “Report” and “Build” back to back in the longest free stretch of the day, 13:00–15:00."),
  ],
};

test("a plan says why it was suggested apart from what sets it apart, in English as the planner wrote it", () => {
  assert.deepEqual(planNotes(focused, t, "en", same), {
    why: "Suggested because you have 2 work, project, and learning tasks to keep together.",
    apart: "Keeps “Report” and “Build” back to back in the longest free stretch of the day, 13:00–15:00.",
    byAgent: false,
  });
});

test("a reason the local model wrote is marked as the agent's, in either language", () => {
  const chosen = { slug: "spacious", notes: [
    note("planWhyAgent", { en: "Your day is light.", zh: "今天任务不多。" }, "Your day is light."),
    note("planDoesSpacious", { gap: 60, end: "15:00" }, "Leaves 60 minutes between tasks."),
  ] };
  assert.deepEqual(planNotes(chosen, t, "en", same), { why: "Your day is light.", apart: "Leaves 60 minutes between tasks.", byAgent: true });
  assert.equal(planNotes(chosen, t, "zh", same).why, 'planWhyAgent {"en":"Your day is light.","zh":"今天任务不多。"}');
});

test("in another language each sentence is worded from its key, with the task titles quoted", () => {
  assert.deepEqual(planNotes(focused, t, "zh", (value) => `~${value}`), {
    why: 'planWhyFocus {"count":2}',
    apart: 'planDoesFocus {"tasks":"“~Report”、“~Build”","start":"13:00","end":"15:00"}',
    byAgent: false,
  });
});

test("a single title is translated but left for the message to quote", () => {
  const gentle = { slug: "gentle", notes: [note("planDoesGentle", { start: "10:00", first: "Walk" }, "…")] };
  assert.equal(planNotes(gentle, t, "zh", (value) => `~${value}`).apart, 'planDoesGentle {"start":"10:00","first":"~Walk"}');
});

test("Balanced has no reason, and a plan saved before notes keeps its rationale as one text", () => {
  const balanced = { slug: "balanced", notes: [note("planDoesBalanced", { start: "09:00" }, "Takes the areas in turn …")] };
  assert.deepEqual(planNotes(balanced, t, "en", same), { why: "", apart: "Takes the areas in turn …", byAgent: false });
  assert.deepEqual(planNotes({ slug: "gentle", rationale: "Older text.", notes: [] }, t, "en", same),
    { why: "", apart: "Older text.", byAgent: false });
});

test("a plan the area agents voted for names them in the interface language", () => {
  const named = (key, values) => (key === "listSeparator" ? "、" : values ? `${key} ${JSON.stringify(values)}` : key);
  const voted = { slug: "focused", notes: [note("planWhyVotes", { names: "Learning and Life", agents: ["learning", "life"] },
    "The area agents' votes put it here: Learning and Life.")] };
  assert.equal(planNotes(voted, named, "en", same).why, "The area agents' votes put it here: Learning and Life.");
  assert.equal(planNotes(voted, named, "zh", same).why,
    'planWhyVotes {"names":"Learning and Life","agents":"agentLearning、agentLife"}');
});

test("a sentence without a wording in the language falls back to the planner's English", () => {
  const unknown = { slug: "early", notes: [note("planDoesSomethingNew", {}, "New sentence.")] };
  assert.equal(planNotes(unknown, (key) => key, "zh", same).apart, "New sentence.");
});
