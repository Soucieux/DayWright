/**
 * Put the day's rows in one shape: a set plan's entries, each carrying its source task's flags,
 * then the user's own tasks the plan doesn't schedule, marked as outside it. A flexible task has no
 * start time until a set plan places it, so it is kept apart from the timed schedule. Agent
 * suggestions still waiting for the user's Accept are not the user's yet, so they come back
 * separately, and so do the set plan's lunch and dinner, which are breaks rather than tasks.
 * @param {object} day - The day from the local service.
 * @returns {{rows: object[], timed: object[], untimed: object[], fromPlan: boolean, suggestions: object[], meals: object[]}}
 *   Every row, timed ones first; the timed rows sorted by start time; the rows without a start
 *   time, in the order they were made; whether rows come from a set plan; the pending suggestions;
 *   and the set plan's meals.
 */
export function dayRows(day) {
  const fromPlan = Boolean(day.confirmedVariantId);
  const setPlan = fromPlan ? (day.variants || []).find((variant) => variant.id === day.confirmedVariantId) : null;
  const accepted = day.dayItems.filter((item) => item.acceptance !== "pending");
  const itemsById = new Map(accepted.map((item) => [item.id, item]));
  const planRows = fromPlan
    ? day.entries.map((entry) => ({ ...entry, kind: "entry", source: itemsById.get(entry.source_item_id) }))
    : [];
  const scheduled = new Set(planRows.map((row) => row.source_item_id));
  const itemRows = accepted.filter((item) => !scheduled.has(item.id))
    .map((item) => ({ ...item, kind: "item", source: item, outsidePlan: fromPlan }));
  const all = [...planRows, ...itemRows];
  const timed = all.filter((row) => row.start_time).sort((a, b) => a.start_time.localeCompare(b.start_time));
  // The Untimed list keeps the order its tasks were made in, which the menu bar's current and next follow.
  const untimed = all.filter((row) => !row.start_time)
    .sort((a, b) => (a.source?.createdAt || "").localeCompare(b.source?.createdAt || ""));
  return {
    rows: [...timed, ...untimed],
    timed,
    untimed,
    fromPlan,
    suggestions: day.dayItems.filter((item) => item.acceptance === "pending"),
    meals: (setPlan?.meals || []).map((meal) => ({ ...meal, id: `meal-${meal.title}`, kind: "meal" })),
  };
}
