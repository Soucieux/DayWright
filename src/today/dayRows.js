/**
 * Put the day's rows in one shape: a set plan's entries, each carrying its source task's flags,
 * then the user's own tasks the plan doesn't schedule, marked as outside it. Agent suggestions
 * still waiting for the user's Accept are not the user's yet, so they come back separately.
 * @param {object} day - The day from the local service.
 * @returns {{rows: object[], fromPlan: boolean, suggestions: object[]}} Rows sorted by start time,
 *   whether they come from a set plan, and the pending suggestions.
 */
export function dayRows(day) {
  const fromPlan = Boolean(day.confirmedVariantId);
  const accepted = day.dayItems.filter((item) => item.acceptance !== "pending");
  const itemsById = new Map(accepted.map((item) => [item.id, item]));
  const planRows = fromPlan
    ? day.entries.map((entry) => ({ ...entry, kind: "entry", source: itemsById.get(entry.source_item_id) }))
    : [];
  const scheduled = new Set(planRows.map((row) => row.source_item_id));
  const itemRows = accepted.filter((item) => !scheduled.has(item.id))
    .map((item) => ({ ...item, kind: "item", source: item, outsidePlan: fromPlan }));
  return {
    rows: [...planRows, ...itemRows].sort((a, b) => a.start_time.localeCompare(b.start_time)),
    fromPlan,
    suggestions: day.dayItems.filter((item) => item.acceptance === "pending"),
  };
}
