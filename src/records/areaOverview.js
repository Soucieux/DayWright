import { formatMinutes, shortDate } from "../time.js";

/**
 * Each area's one-line meaning, by its message key, in the order the purpose rule takes them: a task
 * someone else expects is Work, a step toward something with an end is Project, getting better at
 * something is Learning, and everything else is Life.
 */
export const AREA_MEANINGS = {
  work: "areaMeaningWork", project: "areaMeaningProject", learning: "areaMeaningLearning", life: "areaMeaningLife",
};

/** Each area card's title and the one line saying what it counts, by message key. */
export const CARD_TEXT = {
  today: { title: "areaTodayTitle", counts: "areaTodayCounts" },
  notes: { title: "areaNotesTitle", counts: "areaNotesCounts" },
  subjects: { title: "subjectsTitle", counts: "subjectsCounts" },
  practice: { title: "practiceTitle", counts: "practiceCounts" },
  habits: { title: "habitsTitle", counts: "habitsCounts" },
  shape: { title: "shapeTitle", counts: "shapeCounts" },
  energy: { title: "energyLabel", counts: "energyCounts" },
  load: { title: "loadTitle", counts: "loadCounts" },
  meetings: { title: "meetingsTitle", counts: "meetingsCounts" },
  carryOvers: { title: "carryOversTitle", counts: "carryOversCounts" },
  projects: { title: "projectsTitle", counts: "projectsCounts" },
  nextSteps: { title: "nextStepsTitle", counts: "nextStepsCounts" },
  recentDone: { title: "recentDoneTitle", counts: "recentDoneCounts" },
  library: { title: "librarySection", counts: "libraryCardCounts" },
};

/**
 * Each card's empty state, by message key: what it says, and the link it offers when one helps.
 * Nothing is added from a card: one that fills by adding says to use the area's + Add instead.
 */
export const EMPTY_STATES = {
  today: { text: "areaTodayEmpty" },
  todayPast: { text: "areaPastEmpty", action: "areaSeeAll" },
  notes: { text: "notesNothing", action: "areaAskAva" },
  subjects: { text: "subjectsEmpty" },
  practice: { text: "practiceEmpty" },
  habits: { text: "habitsEmpty" },
  energy: { text: "energyEmpty", action: "areaReportEnergy" },
  load: { text: "loadEmpty" },
  meetings: { text: "meetingsEmpty" },
  carryOvers: { text: "carryOversEmpty", action: "areaSeeAll" },
  projects: { text: "projectsEmpty" },
  nextSteps: { text: "nextStepsEmpty" },
  recentDone: { text: "recentDoneEmpty", action: "areaSeeAll" },
  library: { text: "libraryCardEmpty" },
};

/** The goals Subjects and Projects list before + N more goals. */
export const GOALS_SHOWN = 6;
/** Where a line's title stands while the line is split around it (see aroundTitle): a character no title holds. */
const TITLE_MARK = "\u0000";

/** What an area page's one + Add button adds, in its menu's order, each with its message key and icon. */
export const AREA_ADD_CHOICES = [["task", "addMenuTask", "check"], ["goal", "addMenuGoal", "target"], ["note", "addMenuNote", "note"]];

/**
 * What one area page's + Add offers: a task or a goal everywhere, and a note or file only in Learn, as the
 * Library is for studying.
 * @param {string} domain - The area.
 * @returns {[string, string, string][]} Its choices, from AREA_ADD_CHOICES, in their order.
 */
export function areaAddChoices(domain) {
  return domain === "learning" ? AREA_ADD_CHOICES : AREA_ADD_CHOICES.filter(([choice]) => choice !== "note");
}

/** Every other text the area screens show, by message key. */
const SCREEN_LABELS = [
  "areaDayTitle", "shapeDayTitle", "notesForToday", "notesHow", "subjectTime", "weekTotals", "nextSessionLabel",
  "noSessionPlanned", "noNextStep", "useAddHint", "areaAddLabel", "notInAGoal", "habitDailySince", "habitWeeklySince", "habitStopped", "habitDayDone", "habitDayPartial",
  "habitDayMissed", "habitDayUpcoming", "habitDayOff", "practiceDayPractised", "practiceDayPlanned", "practiceDayNone",
  "bookedLabel", "mealTimeLabel", "freeWindowsLabel", "noFreeWindows", "energyGuide", "energyNoReading", "askAvaToMove",
  "askMoveRequest", "carryPartlyDone", "projectOnTrack", "projectStalled", "projectNoSteps", "stepsDone", "noProjectGoal",
  "dayDotsLabel", "barPlannedDone", "barReading", "notReportedShort", "entryMovedTo", "pausedLabel", "avaNoticeLowEnergy",
  "areaDayStats", "carryCounts", "dayStripBooked", "dayStripWholeKey", "librarySeeAll", "subjectNextLine", "allTasksDone", "noTasksYet",
  "moreGoals", "moreGoalOne", "fewerGoals", "nextStepLabel", "lastStepLabel", "stepsDoneOne", "allTasksDoneOne", "noneThisWeek",
];

/** Every message key the area screens use, so each can be checked in both languages. */
export const AREA_SCREEN_TEXT = [
  ...Object.values(CARD_TEXT).flatMap(({ title, counts }) => [title, counts]),
  ...Object.values(EMPTY_STATES).flatMap(({ text, action }) => (action ? [text, action] : [text])),
  ...AREA_ADD_CHOICES.map(([, key]) => key),
  ...SCREEN_LABELS,
];

/** The icon each kind of agent note shows beside its words. */
const NOTE_ICONS = {
  slipping: "history", "length-off": "clock", "due-for-review": "book", stalled: "pause",
  "low-energy": "sun", "low-energy-full": "sun", "doubt-usual-time": "clock", "doubt-too-short": "clock",
  "energy-short-review": "sparkline", "energy-harder-session": "sparkline", "energy-heavy-load": "sparkline",
  "energy-biggest-work": "sparkline", "energy-small-step": "sparkline", "energy-next-big-step": "sparkline",
};

/** A Monday, from which a weekday's number, 0 for Monday, finds its name. */
const A_MONDAY = "2024-01-01";

const localeOf = (language) => (language === "zh" ? "zh-Hans" : "en-GB");
const dateOf = (value) => new Date(`${value}T12:00:00`);

/**
 * A day's short weekday name, such as Thu or 周四.
 * @param {string} value - The YYYY-MM-DD day.
 * @param {string} language - `en` or `zh`.
 * @returns {string} The weekday's short name.
 */
function weekdayName(value, language) {
  return new Intl.DateTimeFormat(localeOf(language), { weekday: "short" }).format(dateOf(value));
}

/**
 * A day as its date alone, such as 1 Oct or 10月1日.
 * @param {string} value - The YYYY-MM-DD day.
 * @param {string} language - `en` or `zh`.
 * @returns {string} The day and month.
 */
function dayMonth(value, language) {
  return new Intl.DateTimeFormat(localeOf(language), { day: "numeric", month: "short" }).format(dateOf(value));
}

/**
 * Name the days a card covers, the month said once when both ends share it.
 * @param {string} first - The first YYYY-MM-DD day.
 * @param {string} last - The last YYYY-MM-DD day.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Mon 5 – Sun 11 Oct" or "10月5日周一至11日周日".
 */
export function dayRange(first, last, language) {
  const [start, end] = [dateOf(first), dateOf(last)];
  const sameMonth = start.getFullYear() === end.getFullYear() && start.getMonth() === end.getMonth();
  if (language === "zh") {
    return `${shortDate(first, language)}至${sameMonth ? `${end.getDate()}日${weekdayName(last, language)}` : shortDate(last, language)}`;
  }
  return `${sameMonth ? `${weekdayName(first, language)} ${start.getDate()}` : shortDate(first, language)} – ${shortDate(last, language)}`;
}

/**
 * Word a habit's streak: its days done in a row, or its weeks for a weekly repeat.
 * @param {{kind: string, streak: number}} habit - A repeat as Life's overview lists it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} Such as "3-day streak", or that no streak is running.
 */
export function streakText(habit, t) {
  if (!habit.streak) return t("streakNone");
  return t(habit.kind === "weekly" ? "streakWeeks" : "streakDays", { count: habit.streak });
}

/**
 * Say a habit's rule and since when it holds.
 * @param {{kind: string, weekday?: number|null, since: string}} habit - A repeat as Life's overview lists
 *   it; a weekly one has its weekday, 0 for Monday.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Daily since 1 Oct" or "Weekly on Mon since 28 Sept".
 */
export function habitRule(habit, t, language) {
  const date = dayMonth(habit.since, language);
  if (habit.kind !== "weekly") return t("habitDailySince", { date });
  const monday = dateOf(A_MONDAY);
  monday.setDate(monday.getDate() + habit.weekday);
  return t("habitWeeklySince", { weekday: new Intl.DateTimeFormat(localeOf(language), { weekday: "short" }).format(monday), date });
}

/**
 * Say the day a habit stopped this week, if it did.
 * @param {{stoppedOn: string|null}} habit - A repeat as Life's overview lists it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string|null} Such as "Stopped Thu", or null while it repeats.
 */
export function habitStopped(habit, t, language) {
  return habit.stoppedOn ? t("habitStopped", { day: weekdayName(habit.stoppedOn, language) }) : null;
}

/**
 * Say where a Work task carried over from the week before stands.
 * @param {{date: string, movedTo?: string, status?: string}} item - A carry-over as Work's overview lists
 *   it: moved on from a set plan's day (`movedTo`), or not done on its day (`status`).
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} "Not reported", "Partly done", or "Moved to {day}".
 */
export function carryStatusText(item, t, language) {
  if (item.movedTo) return t("entryMovedTo", { day: shortDate(item.movedTo, language) });
  return t(item.status === "partial" ? "carryPartlyDone" : "notReportedShort");
}

/**
 * The request Ask Ava to move types into Ava's box, to send or change before sending.
 * @param {{title: string, date: string}} item - The carried-over task and its day.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Move “Email” from Fri 2 Oct to today".
 */
export function askMoveText(item, t, language) {
  return t("askMoveRequest", { title: item.title, day: shortDate(item.date, language) });
}

/**
 * Say how a project stands, in plain words.
 * @param {{health: string, idleDays: number|null}} project - A project as Project's overview lists it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} "On track", "Stalled N days", "Paused" or "No steps yet".
 */
export function projectStatusText(project, t) {
  if (project.health === "stalled") return t("projectStalled", { days: project.idleDays });
  return t({ "on-track": "projectOnTrack", paused: "pausedLabel", "no-steps": "projectNoSteps" }[project.health]);
}

/**
 * Learn's subjects in the order Subjects lists them: goals with time planned or done this week first, the most
 * planned first; then the rest, the most recently practised first; paused goals last, in the same order among
 * themselves. Goals that tie keep the service's order, oldest first.
 * @param {{status: string, plannedMinutes: number, doneMinutes: number, lastPractised: string|null}[]} subjects - Learning's overview's subjects.
 * @returns {object[]} The same subjects, ordered.
 */
export function subjectOrder(subjects) {
  const active = (subject) => subject.plannedMinutes > 0 || subject.doneMinutes > 0;
  return [...subjects].sort((a, b) => (a.status === "paused") - (b.status === "paused") || active(b) - active(a)
    || (active(a) ? b.plannedMinutes - a.plannedMinutes : 0) || (b.lastPractised || "").localeCompare(a.lastPractised || ""));
}

/**
 * Project's projects in the order Projects lists them: those with a next step first, the soonest first; then
 * stalled goals; then the rest; paused goals last. Goals that tie keep the service's order, oldest first.
 * @param {{health: string, nextStep: {date: string}|null}[]} projects - Project's overview's projects.
 * @returns {object[]} The same projects, ordered.
 */
export function projectOrder(projects) {
  const rank = (project) => (project.health === "paused" ? 3 : project.nextStep ? 0 : project.health === "stalled" ? 1 : 2);
  return [...projects].sort((a, b) => rank(a) - rank(b) || (rank(a) === 0 ? a.nextStep.date.localeCompare(b.nextStep.date) : 0));
}

/**
 * The goals a card lists: the first GOALS_SHOWN, or all of them once opened out, and how many are past the first.
 * @param {object[]} goals - The card's goals, in its order.
 * @param {boolean} all - Whether the card is opened out.
 * @returns {{shown: object[], more: number}} The goals listed, and the count + N more goals names.
 */
export function shownGoals(goals, all) {
  return { shown: all ? goals : goals.slice(0, GOALS_SHOWN), more: Math.max(goals.length - GOALS_SHOWN, 0) };
}

/**
 * Word + N more goals, for one goal or several.
 * @param {number} count - The goals past the first GOALS_SHOWN.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} Such as "+ 1 more goal" or "+ 4 more goals".
 */
export function moreGoalsText(count, t) {
  return count === 1 ? t("moreGoalOne") : t("moreGoals", { count });
}

/**
 * Word a project's steps done of all, for one step or several.
 * @param {{done: number, total: number}} project - A project as Project's overview lists it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} Such as "5 of 8 steps" or "0 of 1 step".
 */
export function stepsText(project, t) {
  return project.total === 1 ? t("stepsDoneOne", { done: project.done }) : t("stepsDone", { done: project.done, total: project.total });
}

/**
 * A line split around the title it names, so a narrow card can cut the title alone with "…" and keep the words
 * before and after it, such as a place and a day, whole.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} key - The line's message key, which holds {title}.
 * @param {object} values - Its values, the title among them.
 * @returns {{head: string, title: string, tail: string}} The words before the title, the title, and the words after.
 */
function aroundTitle(t, key, values) {
  const [head, tail] = t(key, { ...values, title: TITLE_MARK }).split(TITLE_MARK);
  return { head, title: values.title, tail };
}

/**
 * A line with no title to cut, in the shape aroundTitle gives.
 * @param {string} words - The whole line.
 * @returns {{head: string, title: string, tail: string}} The words as its head, with no title or tail.
 */
const wholeLine = (words) => ({ head: words, title: "", tail: "" });

/**
 * Word that every task of a goal is done, for one task or several.
 * @param {number} total - The goal's tasks.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} Such as "All 5 done" or "Its 1 task is done".
 */
export function allDoneText(total, t) {
  return total === 1 ? t("allTasksDoneOne") : t("allTasksDone", { total });
}

/**
 * A subject's time this week: done against planned, or that the week has neither.
 * @param {{plannedMinutes: number, doneMinutes: number}} figures - A subject's, or Not in a goal's, minutes this week.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "1 h of 2 h 30 min", or "None this week".
 */
export function subjectTimeText(figures, t, language) {
  if (!figures.plannedMinutes && !figures.doneMinutes) return t("noneThisWeek");
  return t("subjectTime", { done: formatMinutes(figures.doneMinutes, language), planned: formatMinutes(figures.plannedMinutes, language) });
}

/**
 * A subject's second line, after its dots: its next task to study, with its place among the goal's tasks and
 * its day; that every task is done; or that it has none yet.
 * @param {{tasks: {total: number, next: object|null}|null}} subject - A subject as Learning's overview lists it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @param {(title: string) => string} [demoText] - The demo's wording for a title; the title itself otherwise.
 * @returns {{head: string, title: string, tail: string}} The line around its task's title (see aroundTitle), such as
 *   "Next: " · "Task 2 essay" · " (4 of 9) · Fri 9 Oct"; or "All 5 done" or "No tasks yet" whole.
 */
export function subjectNextText(subject, t, language, demoText = (title) => title) {
  const { tasks } = subject;
  if (!tasks) return wholeLine(t("noTasksYet"));
  if (!tasks.next) return wholeLine(allDoneText(tasks.total, t));
  return aroundTitle(t, "subjectNextLine", { title: demoText(tasks.next.title), number: tasks.next.number, total: tasks.total,
    when: [shortDate(tasks.next.date, language), tasks.next.start_time].filter(Boolean).join(" ") });
}

/**
 * A project's second line: its next step and its day, else its last step done and its day, else that it has no
 * next step.
 * @param {{nextStep: {title: string, date: string}|null, lastStep: {title: string, date: string}|null}} project - A project as Project's overview lists it.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @param {string} language - `en` or `zh`.
 * @param {(title: string) => string} [demoText] - The demo's wording for a title; the title itself otherwise.
 * @returns {{head: string, title: string, tail: string}} The line around its step's title (see aroundTitle), such as
 *   "Next: " · "Draft" · " · Sat 10 Oct"; or "No next step yet" whole.
 */
export function projectLineText(project, t, language, demoText = (title) => title) {
  const step = project.nextStep || project.lastStep;
  if (!step) return wholeLine(t("noNextStep"));
  return aroundTitle(t, project.nextStep ? "nextStepLabel" : "lastStepLabel", { title: demoText(step.title), date: shortDate(step.date, language) });
}

/**
 * The icon an agent note shows for its kind.
 * @param {string} kind - The note's kind, as Ava's messages name it.
 * @returns {string} The icon's name; the agent's own for a kind without one.
 */
export function noteIcon(kind) {
  return NOTE_ICONS[kind] || "agent";
}

/**
 * A length short enough to print above a narrow bar, in hours and minutes.
 * @param {number} minutes - The length; 0 for a day with none.
 * @returns {string} Such as "45m", "1h" or "1h30"; a dash for none.
 */
export function barTime(minutes) {
  if (!minutes) return "–";
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return hours ? `${hours}h${rest ? String(rest).padStart(2, "0") : ""}` : `${rest}m`;
}

/**
 * Group items over days by their day, earliest first, leaving out days with none.
 * @param {{date: string}[]} items - The items, each on its YYYY-MM-DD day.
 * @returns {{date: string, items: object[]}[]} Each day with its items, in the order they came.
 */
export function byDay(items) {
  const dates = [...new Set(items.map((item) => item.date))].sort();
  return dates.map((date) => ({ date, items: items.filter((item) => item.date === date) }));
}
