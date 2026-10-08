import { formatMinutes, shortDate } from "../time.js";

/** A no-break space: a time's words never break across lines. */
export const NBSP = " ";
/** Planned against actual: the fully done tasks a row needs before it is drawn, as the local service counts them. */
export const PAIR_TASKS = 3;
/** Energy and real time: the days a group needs before it is drawn. */
export const ENERGY_DAYS = 3;
/** A Monday, from which a weekday's index (0 for Monday) finds its name. */
const A_MONDAY = "2024-01-01";
/** Each graph's title and the words its threshold takes, by message key. */
const GRAPH_TEXT = {
  bestHours: ["patternBestHours", "thresholdBestHours"], plannedActual: ["patternPairs", "thresholdPairs"],
  estimates: ["patternEstimates", "thresholdEstimates"], outcome: ["patternOutcome", "thresholdOutcome"],
  pace: ["patternPace", "thresholdPace"], energy: ["patternEnergy", "thresholdEnergy"], reporting: ["patternReporting", "thresholdReporting"],
  repeating: ["patternPairs", "thresholdPairsTasks"],
};
/** The still-settling chip's words, by what a graph counts. */
const SETTLING_TEXT = { tasks: "patternsSettlingTasks", days: "patternsSettlingDays", sections: "patternsSettlingSections" };
/** Each energy group's word in a sentence, and its name and range on its row. */
export const ENERGY_GROUPS = {
  low: { word: "patternsGroupLow", name: "patternsLow", range: "1–2" },
  middle: { word: "patternsGroupMiddle", name: "patternsMiddle", range: "3" },
  high: { word: "patternsGroupHigh", name: "patternsHigh", range: "4–5" },
};

const locale = (language) => (language === "zh" ? "zh-Hans" : "en-GB");
const noon = (day) => new Date(`${day}T12:00:00`);
const format = (day, language, options) => new Intl.DateTimeFormat(locale(language), options).format(noon(day));

/**
 * The day a weekday's index falls on, in the week of A_MONDAY.
 * @param {number} index - 0 for Monday to 6 for Sunday.
 * @returns {string} Its YYYY-MM-DD date.
 */
function weekdayDate(index) {
  const day = noon(A_MONDAY);
  day.setDate(day.getDate() + index);
  return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

/** A day and month, such as "7 Sep" or "9月7日". */
const dayMonth = (day, language) => format(day, language, { day: "numeric", month: "short" });
/** An hour as a clock time, such as "10:00". */
const clock = (hour) => `${String(hour).padStart(2, "0")}:00`;
/** A whole number's sign in a change: "+", the minus sign, or nothing at zero. */
const signed = (value) => `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value)}`;

/**
 * Keep a phrase on one line: its spaces become no-break spaces.
 * @param {string} text - Such as "1 h 10 min".
 * @returns {string} The same words, which never break apart.
 */
export function keep(text) {
  return String(text).replace(/ /g, NBSP);
}

/**
 * A time in minutes in words, kept on one line.
 * @param {number} minutes - The minutes.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "1 h 10 min".
 */
export function timeText(minutes, language) {
  return keep(formatMinutes(minutes, language));
}

/**
 * A length in minutes alone, kept on one line, as a comparison reads it: "75 min" beside "you set 60".
 * @param {number} minutes - The minutes.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "75 min" or "75 分钟".
 */
export function minutesText(minutes, language) {
  return keep(language === "zh" ? `${minutes} 分钟` : `${minutes} min`);
}

/**
 * Split a sentence into its plain and bold parts, the bold ones between ** marks.
 * @param {string} text - Such as "Work runs longest: **22% over plan**."
 * @returns {{text: string, strong: boolean}[]} Its parts in order.
 */
export function bold(text) {
  return text.split("**").map((part, index) => ({ text: part, strong: index % 2 === 1 })).filter((part) => part.text);
}

/**
 * What the Patterns tab's range covers.
 * @param {{start: string, end: string}} tab - The period's first and last day.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "7 Sep – 6 Oct · from the times you recorded".
 */
export function rangeCaption(tab, t, language) {
  return t("patternsRange", { start: dayMonth(tab.start, language), end: dayMonth(tab.end, language) });
}

/**
 * The name under a column: a day's weekday letter in a week and its date in a month of days, a week's
 * first day, or a month's short name.
 * @param {{start: string, kind: string}} column - The column, as the local service sends it.
 * @param {object[]} columns - Every column the graph draws.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "T", "10", "7 Sep" or "Sep".
 */
export function columnName(column, columns, language) {
  if (column.kind === "week") return dayMonth(column.start, language);
  if (column.kind === "month") return format(column.start, language, { month: "short" });
  if (columns.length > 7) return String(Number(column.start.slice(-2)));
  return format(column.start, language, { weekday: "narrow" });
}

/**
 * A column's name in its own words, as its marks' labels read it.
 * @param {{start: string, kind: string}} column - The column.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Mon 5 Oct", "Week of 7 Sep" or "September 2026".
 */
export function columnLabel(column, t, language) {
  if (column.kind === "week") return t("patternsWeekOfShort", { date: dayMonth(column.start, language) });
  if (column.kind === "month") return format(column.start, language, { month: "long", year: "numeric" });
  return shortDate(column.start, language);
}

/** A day's name in a finding: its weekday in a week, its date in a longer span. */
function dayName(column, columns, language) {
  return columns.length > 7 ? dayMonth(column.start, language) : format(column.start, language, { weekday: "long" });
}

/**
 * When a column was, as a finding says it: this week or today when it holds today, else the week, day or month.
 * @param {{start: string, end: string, kind: string}} column - The column.
 * @param {object[]} columns - Every column the graph draws; a day among more than seven is named by its date.
 * @param {string} today - Today, YYYY-MM-DD.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "this week", "in the week of 7 Sep", "today", "on Wednesday" or "in September".
 */
export function columnWhen(column, columns, today, t, language) {
  const holdsToday = column.start <= today && today <= column.end;
  if (column.kind === "week") {
    return holdsToday ? t("patternsWhenThisWeek") : t("patternsWhenWeekOf", { date: dayMonth(column.start, language) });
  }
  if (column.kind === "month") {
    return holdsToday ? t("patternsWhenThisMonth") : t("patternsWhenMonth", { month: format(column.start, language, { month: "long" }) });
  }
  return holdsToday ? t("patternsWhenToday") : t("patternsWhenDay", { day: dayName(column, columns, language) });
}

/**
 * What a graph says in place of itself, or beside it, for how far it has come (see patterns.gauge): not
 * enough yet, with how far along; nothing in the range, which a wider range may have; or still settling.
 * @param {string} graph - The graph, as GRAPH_TEXT names it.
 * @param {{state: string, count: number, threshold: number, unit: string, basis: number}} gauge - Its gauge.
 * @param {"week"|"month"|"all"} period - The range on show.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {{state: string, text: string|null, chip: string|null, progress: {count: number, threshold: number, text: string}|null}}
 *   The words in place of the graph, its chip, and the progress toward its threshold.
 */
export function stateNote(graph, gauge, period, t) {
  const none = { state: gauge.state, text: null, chip: null, progress: null };
  if (gauge.state === "ready") return none;
  if (gauge.state === "settling") return { ...none, chip: t(SETTLING_TEXT[gauge.unit], { count: gauge.basis }) };
  if (gauge.state === "empty" && period !== "all") return { ...none, text: t(period === "week" ? "patternsNothingWeek" : "patternsNothingMonth") };
  const [title, threshold] = GRAPH_TEXT[graph];
  return { ...none, text: t("patternsAppears", { graph: t(title), threshold: t(threshold, { count: gauge.threshold }), count: gauge.count }),
    progress: { count: gauge.count, threshold: gauge.threshold, text: t("patternsProgress", { count: gauge.count, threshold: gauge.threshold }) } };
}

/** What Ask Ava sends from the note, by period: the times of the days shown, or every one on All time. */
const CHECK_PROMPTS = { week: "patternsCheckPromptWeek", month: "patternsCheckPromptMonth", all: "patternsCheckPromptAll" };

/**
 * The note under the range when times are left out of the graphs: every one, and how many of them belong to
 * tasks that need a status before their time can be checked.
 * @param {number} count - The times left out.
 * @param {number} needsStatus - How many of them need a status first.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {string} Such as "3 times to check are left out of these graphs · 1 needs a status first".
 */
export function toCheckNote(count, needsStatus, t) {
  const left = count === 1 ? t("patternsToCheckOne") : t("patternsToCheck", { count });
  if (!needsStatus) return left;
  return `${left} · ${needsStatus === 1 ? t("patternsNeedsStatusOne") : t("patternsNeedsStatus", { count: needsStatus })}`;
}

/**
 * What Ask Ava sends from the note: it lists the same times the note counts, for the days the period shows.
 * @param {"week"|"month"|"all"} period - The period on show.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {string} Such as "Check my times for these 7 days".
 */
export function checkPrompt(period, t) {
  return t(CHECK_PROMPTS[period]);
}

/**
 * The day Catch up starts from: the earliest with a task that needs a status before its time can be checked.
 * @param {{date: string, needsStatus: boolean}[]} [checks] - The times left out, oldest day first.
 * @returns {string|null} Its YYYY-MM-DD date, or null with none.
 */
export function catchUpDay(checks) {
  return checks?.find((check) => check.needsStatus)?.date ?? null;
}

/** A weekday as a habit names it: "Tuesdays", or in Chinese "周二". */
function weekdayPlural(index, language) {
  return language === "zh" ? format(weekdayDate(index), language, { weekday: "short" })
    : `${format(weekdayDate(index), language, { weekday: "long" })}s`;
}

/**
 * Best hours' finding: the best window or windows, and the busiest weekday unless the days are spread evenly.
 * @param {object} finding - As patterns.best_hours gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{text: string, strong: boolean}[]} The sentence.
 */
export function bestHoursLead(finding, t, language) {
  if (finding.kind === "oneHour") return bold(t("patternsOneHour", { hour: clock(finding.hour) }));
  const weekday = finding.day == null ? "" : t("patternsBestDay", { day: weekdayPlural(finding.day, language) });
  return bold(finding.kind === "window"
    ? t("patternsBestWindow", { from: clock(finding.from), to: clock(finding.to), day: weekday })
    : t("patternsBestWindows", { first: clock(finding.hours[0]), second: clock(finding.hours[1]), day: weekday }));
}

/**
 * A Best hours cell's words, which its tip shows too.
 * @param {number} weekday - 0 for Monday to 6 for Sunday.
 * @param {number} hour - The hour it starts.
 * @param {number} count - Fully done tasks finished in it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Fri 10:00–11:00 · 3 tasks finished".
 */
export function cellLabel(weekday, hour, count, t, language) {
  const values = { day: format(weekdayDate(weekday), language, { weekday: "short" }), from: clock(hour), to: clock(hour + 1), count };
  return t(count === 0 ? "patternsCellNone" : count === 1 ? "patternsCellOne" : "patternsCell", values);
}

/**
 * The short name of each weekday, Monday first, as Best hours' rows show them.
 * @param {string} language - `en` or `zh`.
 * @returns {string[]} Such as "Mon" or "周一".
 */
export function weekdayNames(language) {
  return [0, 1, 2, 3, 4, 5, 6].map((index) => format(weekdayDate(index), language, { weekday: "short" }));
}

/**
 * Best hours' key: each step's counts, then what they count.
 * @param {{step: number, from: number, to: number}[]} key - As patterns.best_hours gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {{steps: string[], unit: string}} Such as ["1", "2–3"] and "tasks an hour".
 */
export function heatKey(key, t) {
  return { steps: key.map((step) => (step.from === step.to ? `${step.from}` : `${step.from}–${step.to}`)), unit: t("patternsHeatUnit") };
}

/**
 * Planned against actual's finding: the area furthest over or under plan, or how close every row is; on an
 * area page, what a repeating task usually takes.
 * @param {object} finding - As patterns.planned_actual gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @param {boolean} [byTask=false] - Whether the rows are repeating tasks.
 * @returns {{text: string, strong: boolean}[]} The sentence.
 */
export function pairsLead(finding, t, language, byTask = false) {
  if (finding.kind === "usual") {
    return bold(t("patternsUsual", { title: finding.title, actual: minutesText(finding.actual, language), planned: finding.planned }));
  }
  if (finding.kind === "close") return bold(t(byTask ? "patternsCloseTasks" : "patternsClose"));
  const name = finding.title ?? t(finding.key);
  return bold(t(finding.kind === "over" ? "patternsOver" : "patternsUnder", { area: name, percent: Math.abs(finding.percent) }));
}

/**
 * A planned against actual row's figures, or what it still needs.
 * @param {{planned: number|null, actual: number|null, percent: number|null, count: number}} row - As patterns.planned_actual gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{value: string|null, detail: string|null, needs: string|null}} Such as "50 → 55 min" and "+10% · 7 done".
 */
export function pairValue(row, t, language) {
  if (row.planned == null) return { value: null, detail: null, needs: t("patternsPairNeeds", { threshold: PAIR_TASKS, count: row.count }) };
  return { value: t("patternsPairValue", { planned: row.planned, actual: minutesText(row.actual, language) }),
    detail: t("patternsPairDetail", { change: `${signed(row.percent)}%`, count: row.count }), needs: null };
}

/**
 * Estimates improving's finding: the latest column's gap against the earliest's.
 * @param {object} finding - As patterns.estimates gives it.
 * @param {object[]} columns - The graph's columns.
 * @param {string} today - Today, YYYY-MM-DD.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{text: string, strong: boolean}[]} The sentence.
 */
export function estimatesLead(finding, columns, today, t, language) {
  if (finding.kind === "spot") return bold(t("patternsEstSpot"));
  const now = minutesText(finding.now, language);
  if (finding.kind === "same") return bold(t("patternsEstSame", { now }));
  const column = columns[finding.column];
  const holdsToday = column.start <= today && today <= column.end;
  const subject = column.kind === "week"
    ? (holdsToday ? t("patternsEstThisWeek") : t("patternsEstWeekOf", { date: dayMonth(column.start, language) }))
    : (holdsToday ? t("patternsEstToday") : t("patternsEstDay", { day: dayName(column, columns, language) }));
  if (finding.kind === "single") return bold(t("patternsEstSingle", { subject, now }));
  return bold(t(finding.kind === "down" ? "patternsEstDown" : "patternsEstUp",
    { subject, now, before: finding.before, when: columnWhen(columns[finding.beforeColumn], columns, today, t, language) }));
}

/**
 * Time by outcome's finding: fully done time's share, and the time left without a status when there is any.
 * @param {{share: number, noReply: number}} finding - As patterns.outcome gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{text: string, strong: boolean}[]} The sentence.
 */
export function outcomeLead(finding, t, language) {
  return bold(finding.noReply
    ? t("patternsOutcomeNoReply", { share: finding.share, minutes: timeText(finding.noReply, language) })
    : t("patternsOutcome", { share: finding.share }));
}

/**
 * Energy and real time's finding, or the shorter line Life's Energy card adds.
 * @param {object} finding - As patterns.energy gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {boolean} [short=false] - The Energy card's line, without "than planned".
 * @returns {{text: string, strong: boolean}[]} The sentence.
 */
export function energyLead(finding, t, short = false) {
  if (finding.kind === "hardly") return bold(t("patternsEnergyHardly"));
  if (finding.kind === "never") return bold(t("patternsEnergyNever"));
  const key = `patternsEnergy${finding.kind === "longer" ? "Longer" : "Shorter"}${short ? "Short" : ""}`;
  return bold(t(key, { group: t(ENERGY_GROUPS[finding.group].word), percent: Math.abs(finding.percent) }));
}

/**
 * Reporting habit's finding: the latest column's share set right away against the earliest's, and the tasks
 * that got no status; it never judges.
 * @param {object} finding - As patterns.reporting gives it.
 * @param {object[]} columns - The graph's columns.
 * @param {string} today - Today, YYYY-MM-DD.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{text: string, strong: boolean}[]} The sentence.
 */
export function reportingLead(finding, columns, today, t, language) {
  const when = columnWhen(columns[finding.column], columns, today, t, language);
  let sentence = t("patternsReportSingle", { now: finding.now, when });
  if (finding.before != null) {
    const key = finding.now > finding.before ? "patternsReportUp" : finding.now < finding.before ? "patternsReportDown" : "patternsReportSame";
    sentence = t(key, { now: finding.now, when, before: finding.before,
      beforeWhen: columnWhen(columns[finding.beforeColumn], columns, today, t, language) });
  }
  if (!finding.noReply) return bold(sentence);
  const tail = finding.noReply === 1 ? t("patternsNoStatusOne") : t("patternsNoStatus", { count: finding.noReply });
  return bold(language === "zh" ? `${sentence}${tail}` : `${sentence} ${tail}`);
}

/**
 * Section pace's finding: the fastest source, or the one there is.
 * @param {{kind: string, title: string, minutes: number}} finding - As patterns.section_pace gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{text: string, strong: boolean}[]} The sentence.
 */
export function paceLead(finding, t, language) {
  return bold(t(finding.kind === "fastest" ? "patternsPaceFastest" : "patternsPaceOne",
    { title: finding.title, minutes: minutesText(finding.minutes, language) }));
}

/**
 * A Section pace row's words: its accessible name, which its tip shows, its minutes a section and its sections.
 * @param {{title: string, minutes: number, sections: number}} row - As patterns.section_pace gives it.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{label: string, value: string, sections: string}} Such as "Directives: about 8 min a section, 3 sections".
 */
export function paceRow(row, t, language) {
  return { label: t("patternsPaceRow", { title: row.title, minutes: formatMinutes(row.minutes, language), count: row.sections }),
    value: minutesText(row.minutes, language), sections: t("patternsPaceSections", { count: row.sections }) };
}

/**
 * A learning task's line: what its sections still unticked will take at its source's pace, or that they are
 * all ticked; none until its source has a pace.
 * @param {{minutes: number}|null} pace - The source's minutes a section (see patterns.source_pace).
 * @param {{done: number, total: number}} progress - The task's checklist so far.
 * @param {number} taskMinutes - The task's length.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {{text: string, strong: boolean}[]|null} The line, or null.
 */
export function taskPaceLine(pace, progress, taskMinutes, t, language) {
  if (!pace) return null;
  const sections = progress.total - progress.done;
  if (sections <= 0) return bold(t("patternsTaskPaceDone"));
  const left = minutesText(sections * pace.minutes, language);
  if (sections * pace.minutes > taskMinutes) return bold(t("patternsTaskPaceOver", { left, length: minutesText(taskMinutes, language) }));
  if (sections === 1) return bold(t("patternsTaskPaceOne", { left }));
  return bold(t("patternsTaskPace", { minutes: minutesText(pace.minutes, language), left, count: sections }));
}
