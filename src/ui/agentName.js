/** Message keys naming each local agent, by the key the local service reports. */
const AGENT_NAME_KEYS = {
  orchestrator: "agentOrchestrator", learning: "agentLearning", life: "agentLife",
  finance: "agentFinance", summary: "summaryAgent",
};

/**
 * Name a local agent in the interface language.
 * @param {string} key - The agent's key, such as `learning`.
 * @param {(key: string) => string} t - The interface text lookup.
 * @returns {string} The agent's name; an unknown key is shown as it is.
 */
export function agentName(key, t) {
  return AGENT_NAME_KEYS[key] ? t(AGENT_NAME_KEYS[key]) : key;
}
