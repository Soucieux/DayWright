/**
 * Read what a proposed change would do, from the proposal and the day it belongs to.
 * @param {{actionType: string, payload: object}} proposal - A change the agents proposed.
 * @param {{id: string, title: string, duration_minutes: number}[]} dayItems - The tasks of the day on show.
 * @returns {object} `kind` is `set` (set a plan: `to`), `replace` (replace the set plan: `from`,
 *   `to`), `shorten` (shorten a future task: `title`, `from` and `to` in minutes, with `title` and
 *   `from` null when the task isn't on the day on show) or `other`; each carries its `date`.
 */
export function proposalView(proposal, dayItems) {
  const { actionType, payload } = proposal;
  if (actionType === "select_variant") {
    return payload.reviewedFromVariantName
      ? { kind: "replace", date: payload.date, from: payload.reviewedFromVariantName, to: payload.variantName }
      : { kind: "set", date: payload.date, to: payload.variantName };
  }
  if (actionType === "shorten_future_item") {
    const item = dayItems.find((entry) => entry.id === payload.itemId);
    return { kind: "shorten", date: payload.date, title: item?.title ?? null, from: item?.duration_minutes ?? null, to: payload.durationMinutes };
  }
  return { kind: "other", date: payload?.date ?? null };
}
