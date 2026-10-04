/**
 * What a goal's task list offers for one of its tasks. A past task is history: it is changed only
 * through Ava, so the list offers only to delete it; a task today or later can be edited.
 * @param {{date: string}} item - The linked task.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @returns {"delete"|"edit"} The task's action.
 */
export function goalTaskAction(item, today) {
  return item.date < today ? "delete" : "edit";
}

/** How many linked tasks a goal card lists, and keeps room for, so every card is the same height. */
export const CARD_TASKS = 3;

/**
 * The linked tasks a goal card lists: today's and later ones by date first, then the most recent
 * past ones, up to CARD_TASKS.
 * @param {{date: string, startTime: string|null}[]} linked - The goal's tasks.
 * @param {string} today - Today's YYYY-MM-DD date.
 * @returns {{shown: object[], total: number, more: boolean}} The tasks the card lists, how many the
 *   goal has, and whether there are more than it lists.
 */
export function cardTasks(linked, today) {
  const compare = (first, second) => (first < second ? -1 : first > second ? 1 : 0);
  // By day, forward or back, then by start the same way; a task with no start comes last in its day.
  const order = (direction) => (first, second) => direction * compare(first.date, second.date)
    || compare(!first.startTime, !second.startTime) || direction * compare(first.startTime, second.startTime);
  const ahead = linked.filter((item) => item.date >= today).sort(order(1));
  const past = linked.filter((item) => item.date < today).sort(order(-1));
  return { shown: [...ahead, ...past].slice(0, CARD_TASKS), total: linked.length, more: linked.length > CARD_TASKS };
}

/**
 * The words that refuse a goal's removal while tasks still link to it, for one task or several.
 * @param {number} count - How many tasks link to the goal.
 * @returns {{body: string, action: string}} The message keys of the refusal's body and of its way forward.
 */
export function stillLinkedKeys(count) {
  return count === 1
    ? { body: "goalStillLinkedOne", action: "showLinkedTaskOne" }
    : { body: "goalStillLinked", action: "showLinkedTasks" };
}
