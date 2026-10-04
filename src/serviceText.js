/** Refusals from the local service that the interface words in the user's language, by the service's own text. */
const SERVICE_REFUSALS = {
  "A past task changes only through Ava; ask Ava to change it": "pastTaskThroughAva",
};

/**
 * The interface's own words for a refusal from the local service, so it reads in the user's language.
 * @param {string} message - The service's message.
 * @returns {string|null} The message key, or null for a message shown as the service wrote it.
 */
export function refusalKey(message) {
  return SERVICE_REFUSALS[message] ?? null;
}
