/** Message keys naming each local agent, by the key the local service reports. */
const AGENT_NAME_KEYS = {
  orchestrator: "agentOrchestrator", learning: "agentLearning", life: "agentLife",
  work: "agentWork", project: "agentProject", summary: "summaryAgent",
};

/** Message keys for each agent's one job, in a line. */
const AGENT_ROLE_KEYS = {
  orchestrator: "agentRoleOrchestrator", learning: "agentRoleLearning", life: "agentRoleLife",
  work: "agentRoleWork", project: "agentRoleProject", summary: "agentRoleSummary",
};

/**
 * The Orchestrator now runs once in a route. A route saved before also closed with an Orchestrator
 * run, which keeps its step's name so its two rows read differently.
 */
const ORCHESTRATOR_STEP_KEYS = { synthesis: "agentStepFinish" };

/**
 * Name a local agent in the interface language.
 * @param {string} key - The agent's key, such as `learning`.
 * @param {(key: string) => string} t - The interface text lookup.
 * @param {string} [phase] - The run's phase, such as `dispatch`, or `synthesis` in a route saved before.
 * @returns {string} The agent's name, such as "Orchestrator"; an unknown key is shown as it is.
 */
export function agentName(key, t, phase) {
  const name = AGENT_NAME_KEYS[key] ? t(AGENT_NAME_KEYS[key]) : key;
  const step = key === "orchestrator" && ORCHESTRATOR_STEP_KEYS[phase];
  return step ? `${name} · ${t(step)}` : name;
}

/**
 * Say an agent's one job in a line, for under its name in a route.
 * @param {string} key - The agent's key, such as `summary`.
 * @param {(key: string) => string} t - The interface text lookup.
 * @returns {string} The role, or nothing for an agent DayWright no longer has.
 */
export function agentRole(key, t) {
  return AGENT_ROLE_KEYS[key] ? t(AGENT_ROLE_KEYS[key]) : "";
}
