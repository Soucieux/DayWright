import { localDateOf } from "../time.js";

/**
 * What "From a source" sends to make goals: each ticked entry, a connected folder's file whole or a
 * source's first-level heading by its place in the source.
 * @param {{key: string, sourceId: string, index: number|null}[]} entries - The entries listed to tick.
 * @param {Set<string>} ticked - The keys of the entries ticked.
 * @returns {{sourceId: string, index?: number}[]} One pick per goal to make, in the entries' order.
 */
export function goalPicks(entries, ticked) {
  return entries.filter((entry) => ticked.has(entry.key))
    .map(({ sourceId, index }) => (index === null || index === undefined ? { sourceId } : { sourceId, index }));
}

/**
 * A goal's topics as its burn-up counts them: a topic studied is done on the day it was, one planned is
 * planned on its day, and one neither still counts toward all of them, from the day the goal was made.
 * @param {{startAt: string, topics?: {studiedOn: string|null, plannedOn: string|null}[]}} goal - The goal.
 * @returns {{date: string, status: string}[]|null} One per topic, or null for a goal without topics.
 */
export function topicBurnupItems(goal) {
  if (!goal.topics?.length) return null;
  return goal.topics.map((topic) => (topic.studiedOn ? { date: topic.studiedOn, status: "done" }
    : topic.plannedOn ? { date: topic.plannedOn, status: "planned" } : { date: localDateOf(goal.startAt), status: "open" }));
}

/**
 * How far a goal's topics have come: how many are studied, of how many, and the first not yet studied.
 * @param {{studied: boolean}[]} topics - The goal's topics, in order.
 * @returns {{studied: number, total: number, next: object|null}} The counts and the next topic, if any.
 */
export function topicSummary(topics) {
  return { studied: topics.filter((topic) => topic.studied).length, total: topics.length,
    next: topics.find((topic) => !topic.studied) || null };
}
