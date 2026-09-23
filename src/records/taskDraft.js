/** Where a new task starts and how long it lasts until the user says otherwise. */
const NEW_TASK_START = "09:00";
const NEW_TASK_MINUTES = 30;

/**
 * Turn a stored task into editable fields, or start a blank task for a date.
 * @param {object|null} item - The stored task, or null for a new one.
 * @param {string} date - The date a new task belongs to.
 * @param {string} [domain="life"] - The area a new task starts in.
 * @param {string} [goalId=""] - A goal a new task starts linked to.
 * @returns {object} Form fields.
 */
export function taskDraft(item, date, domain = "life", goalId = "") {
  return item ? {
    date: item.date, title: item.title, detail: item.detail, domain: item.domain,
    startTime: item.start_time, durationMinutes: item.duration_minutes,
    constraintKind: item.constraint_kind, repeatKind: item.repeatKind,
    protected: Boolean(item.protected), goalId: item.goalId || "", status: item.completion_status,
  } : {
    date, title: "", detail: "", domain, startTime: NEW_TASK_START,
    durationMinutes: NEW_TASK_MINUTES, constraintKind: "flexible", repeatKind: "none",
    protected: false, goalId, status: "planned",
  };
}

/**
 * Shape form fields into the task the local service stores.
 * @param {object} draft - Form fields from `taskDraft`.
 * @returns {object} The payload for creating or updating a task.
 */
export function taskPayload(draft) {
  return { ...draft, goalId: draft.goalId || null, durationMinutes: Number(draft.durationMinutes) };
}

/**
 * The goals a task in one area may link to: active goals in that same area.
 * @param {object[]} goals - The user's goals.
 * @param {string} domain - The task's area.
 * @returns {object[]} The goals it can link to.
 */
export function linkableGoals(goals, domain) {
  return goals.filter((goal) => goal.domain === domain && goal.status === "active");
}
