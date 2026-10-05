import { formatMinutes, shortDate } from "../time.js";
import { planName } from "./planName.js";

/** The message key wording each kind of finding an area agent makes about a task or its area. */
const FINDING_KEYS = {
  shorten: "findingShorten", "asked-shorter": "findingAskedShorter", hold: "findingHold", keep: "findingKeep",
  mixed: "findingMixed", unreported: "findingUnreported", new: "findingNew", time: "findingTime",
  "area-work": "findingAreaWork",
};

/** How a task has gone lately, said only when it has changed: a steady task needs no mention. */
const TREND_KEYS = { slipping: "findingTrendSlipping", improving: "findingTrendImproving" };

/** Why a task an agent found often unfinished still keeps its length. */
const HOLD_REASON_KEYS = { fixed: "holdFixed", yours: "holdYours", minimum: "holdMinimum" };

/**
 * Word the Life agent's finding: the latest energy reported, its repeats, and whether a lighter day is advised.
 * @param {object} finding - An `area-life` finding.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`, for the date.
 * @returns {string} The sentence.
 */
function lifeText(finding, t, language) {
  const parts = [
    finding.energy != null && t("findingEnergyOn", { date: shortDate(finding.date, language), energy: finding.energy }),
    finding.repeatsScheduled > 0 && t("findingRepeats", { done: finding.repeatsDone, total: finding.repeatsScheduled }),
  ].filter(Boolean);
  return parts.join(t("clauseSeparator")) + (finding.lighter ? t("findingLighter") : "");
}

/**
 * Word the Learning agent's finding: when anything was last practised, and its goals due for review.
 * @param {object} finding - An `area-learning` finding.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`, for the date.
 * @param {(value: string) => string} demoText - Translates the demo workspace's own words.
 * @returns {string} The sentence.
 */
function learningText(finding, t, language, demoText) {
  return [
    finding.lastPractised && t("findingLastPractised", { date: shortDate(finding.lastPractised, language) }),
    finding.due.length > 0 && t("findingDueForReview", { subjects: finding.due.map(demoText).join(t("listSeparator")) }),
  ].filter(Boolean).join(t("clauseSeparator"));
}

/**
 * Word one of an area agent's findings in the interface language, from its own numbers.
 * @param {object} finding - A finding from a plan's agent route.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`, for lengths of time.
 * @param {(value: string) => string} demoText - Translates the demo workspace's own words.
 * @returns {string} The sentence, or nothing for a kind this interface doesn't know.
 */
export function findingText(finding, t, language, demoText) {
  if (finding.kind === "area-life") return lifeText(finding, t, language);
  if (finding.kind === "area-learning") return learningText(finding, t, language, demoText);
  const key = FINDING_KEYS[finding.kind];
  if (!key) return "";
  const minutes = (value) => (value == null ? undefined : formatMinutes(value, language));
  const text = t(key, {
    ...finding,
    task: finding.taskTitle && demoText(finding.taskTitle),
    from: minutes(finding.fromMinutes),
    to: minutes(finding.toMinutes),
    minutes: minutes(finding.minutes),
    time: finding.preferredStart,
    reason: finding.reason && t(HOLD_REASON_KEYS[finding.reason]),
  });
  const withStep = finding.firstStep ? text + t("findingFirstStep", { step: demoText(finding.firstStep) }) : text;
  return TREND_KEYS[finding.trend] ? withStep + t(TREND_KEYS[finding.trend]) : withStep;
}

/**
 * Find what the area agents said about one task, of the given kinds, across a plan's route.
 * @param {object[]|undefined} route - The agents' runs that proposed the plan.
 * @param {string} title - The task's title.
 * @param {string} domain - The task's area.
 * @param {string[]} kinds - The kinds of finding wanted, such as `shorten` or `time`.
 * @returns {object[]} The matching findings, in route order.
 */
export function findingsFor(route, title, domain, kinds) {
  return (route || []).flatMap((run) => run.findings || [])
    .filter((finding) => finding.taskTitle === title && finding.domain === domain && kinds.includes(finding.kind));
}

/**
 * Say which plans an area agent voted for, best first, for the Orchestrator to decide among.
 * @param {{kind: string}[]|undefined} votes - The agent's votes in a plan's route.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {(value: string) => string} demoText - Translates demo workspace text.
 * @returns {string} The line, or nothing when the agent had no task to vote for.
 */
export function votesText(votes, t, demoText) {
  if (!votes?.length) return "";
  return t("agentVotes", { plans: votes.map((vote) => planName({ slug: vote.kind }, t, demoText)).join(t("listSeparator")) });
}
