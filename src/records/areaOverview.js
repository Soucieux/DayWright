import { shortDate } from "../time.js";

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

/** Each card's empty state: what it says to fill it, and the action that does, by message key. */
export const EMPTY_STATES = {
  today: { text: "areaTodayEmpty", action: "addTaskAction" },
  todayPast: { text: "areaPastEmpty", action: "areaSeeAll" },
  notes: { text: "notesNothing", action: "areaAskAva" },
  subjects: { text: "subjectsEmpty", action: "areaNewGoal" },
  practice: { text: "practiceEmpty", action: "addTaskAction" },
  habits: { text: "habitsEmpty", action: "addTaskAction" },
  energy: { text: "energyEmpty", action: "areaReportEnergy" },
  load: { text: "loadEmpty", action: "addTaskAction" },
  meetings: { text: "meetingsEmpty", action: "addTaskAction" },
  carryOvers: { text: "carryOversEmpty", action: "areaSeeAll" },
  projects: { text: "projectsEmpty", action: "areaNewGoal" },
  nextSteps: { text: "nextStepsEmpty", action: "addTaskAction" },
  recentDone: { text: "recentDoneEmpty", action: "areaSeeAll" },
  library: { text: "libraryCardEmpty", action: "addAction" },
};

/** Every other text the area screens show, by message key. */
const SCREEN_LABELS = [
  "areaDayTitle", "shapeDayTitle", "notesForToday", "notesHow", "subjectTime", "weekTotals", "nextSessionLabel",
  "addSessionLabel", "notInAGoal", "habitDailySince", "habitWeeklySince", "habitStopped", "habitDayDone", "habitDayPartial",
  "habitDayMissed", "habitDayUpcoming", "habitDayOff", "practiceDayPractised", "practiceDayPlanned", "practiceDayNone",
  "bookedLabel", "mealTimeLabel", "freeWindowsLabel", "noFreeWindows", "energyGuide", "energyNoReading", "askAvaToMove",
  "askMoveRequest", "carryPartlyDone", "projectOnTrack", "projectStalled", "projectNoSteps", "stepsDone", "noProjectGoal",
  "dayDotsLabel", "barPlannedDone", "barReading", "notReportedShort", "entryMovedTo", "pausedLabel", "avaNoticeLowEnergy",
  "areaDayStats", "carryCounts", "dayStripBooked", "dayStripWholeKey", "librarySeeAll",
];

/** Every message key the area screens use, so each can be checked in both languages. */
export const AREA_SCREEN_TEXT = [
  ...Object.values(CARD_TEXT).flatMap(({ title, counts }) => [title, counts]),
  ...Object.values(EMPTY_STATES).flatMap(({ text, action }) => [text, action]),
  ...SCREEN_LABELS,
];

/** The icon each kind of agent note shows beside its words. */
const NOTE_ICONS = {
  slipping: "history", "length-off": "clock", "due-for-review": "book", stalled: "pause", "day-wont-fit": "alert",
  "low-energy": "sun", "low-energy-full": "sun", "doubt-usual-time": "clock", "doubt-too-short": "clock",
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
