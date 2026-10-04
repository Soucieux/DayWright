import assert from "node:assert/strict";
import test from "node:test";
import { agentName, agentRole } from "../src/ui/agentName.js";

const t = (key) => key;

test("the Orchestrator runs once, so its name carries no step", () => {
  assert.equal(agentName("orchestrator", t, "dispatch"), "agentOrchestrator");
  assert.equal(agentName("orchestrator", t), "agentOrchestrator");
});

test("a route saved before keeps its closing Orchestrator step", () => {
  assert.equal(agentName("orchestrator", t, "synthesis"), "agentOrchestrator · agentStepFinish");
});

test("every agent has a one-line role, and an unknown one has none", () => {
  for (const key of ["orchestrator", "learning", "life", "work", "project", "summary"]) {
    assert.match(agentRole(key, t), /^agentRole[A-Z]/, key);
  }
  assert.equal(agentRole("finance", t), "");
});
