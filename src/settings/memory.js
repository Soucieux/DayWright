/**
 * How the interface words what Ava remembers (the local service keeps it; see backend/app/memory.py): a rule's kind,
 * what it holds and its days, a note's area and words, an end date and the day each was said, in English or Chinese;
 * and whether a rule has every field its kind needs. Nothing here reads or keeps an entry.
 */

/** Each kind of rule, by the key it is worded under. */
export const RULE_KINDS = { "keep-free": "ruleKeepFree", "keep-off": "ruleKeepOff", "finish-by": "ruleFinishBy" };
/** The fields each kind of rule needs, as the service checks them; "area" is an area, or a task by its title. */
export const RULE_FIELDS = { "keep-free": ["start", "end", "days"], "keep-off": ["area", "days"], "finish-by": ["latest", "days"] };
/** The areas a note is tagged with, in the order Settings groups them; a rule keeps one of the first four off. */
export const MEMORY_AREAS = ["learning", "life", "work", "project", "general"];
/** How each field a rule still needs is named when a card says so. */
const NEEDED = { start: "needFieldStart", end: "needFieldEnd", latest: "needFieldLatest", days: "needFieldDays", area: "needFieldArea" };
const CLOCK = /^([01]\d|2[0-3]):[0-5]\d$|^24:00$/;

/**
 * A weekday's short name.
 * @param {number} day - 0 for Monday to 6 for Sunday.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Mon" or "周一".
 */
export function dayName(day, language) {
  // 1 January 2024 was a Monday.
  return new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { weekday: "short" }).format(new Date(2024, 0, 1 + day, 12));
}

/**
 * Days as an entry reads them: every day, or runs of days, the rest listed.
 * @param {number[]} days - Weekdays, 0 for Monday.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Every day", "Mon–Fri" or "Mon, Wed, Fri".
 */
export function daysText(days, t, language) {
  const sorted = [...new Set(days || [])].sort((first, second) => first - second);
  if (sorted.length === 7) return t("memoryEveryDay");
  const runs = [];
  for (const day of sorted) {
    const last = runs.at(-1);
    if (last && day === last.at(-1) + 1) last.push(day);
    else runs.push([day]);
  }
  const span = language === "zh" ? "至" : "–";
  return runs.map((run) => (run.length > 1 ? `${dayName(run[0], language)}${span}${dayName(run.at(-1), language)}`
    : dayName(run[0], language))).join(language === "zh" ? "、" : ", ");
}

/**
 * A day as memory names it, without its weekday.
 * @param {string} day - YYYY-MM-DD.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "31 Dec" or "12月31日".
 */
export function shortDay(day, language) {
  return new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { day: "numeric", month: "short" })
    .format(new Date(`${day}T12:00:00`));
}

/**
 * What a rule holds: its times, the area or task it keeps off, or the time the day is done by.
 * @param {object} rule - The rule.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {string} Such as "18:00–19:00", "Work" or "“Gym”".
 */
export function ruleWhat(rule, t) {
  if (rule.ruleKind === "keep-free") return `${rule.start}–${rule.end}`;
  if (rule.ruleKind === "finish-by") return rule.latest;
  return rule.area ? t(rule.area) : `“${rule.task}”`;
}

/**
 * An entry's area tag as Settings and cards show it.
 * @param {string} area - One of MEMORY_AREAS.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @returns {string} Such as "Learn" or "General".
 */
export function areaName(area, t) {
  return area === "general" ? t("areaGeneral") : t(area);
}

/**
 * An entry in one line, as Ava's cards name it.
 * @param {object} entry - A note or a rule, with its end, if any.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "Rule · Keep free · 18:00–19:00 · Mon–Fri · until 31 Dec", or "Note · Learn · I study best in the morning".
 */
export function entryLine(entry, t, language) {
  const until = entry.endsOn ? [t("memoryUntil", { date: shortDay(entry.endsOn, language) })] : [];
  if (entry.kind === "note") return [t("memoryNote"), areaName(entry.area, t), entry.wording, ...until].join(" · ");
  return [t("memoryRule"), t(RULE_KINDS[entry.ruleKind]), ruleWhat(entry, t), daysText(entry.days, t, language), ...until]
    .join(" · ");
}

/**
 * The fields a rule still lacks for its kind, in the order a card asks for them.
 * @param {{ruleKind: string, start?: string, end?: string, latest?: string, days?: number[], area?: string, task?: string}} rule - The rule.
 * @returns {string[]} Such as ["start", "end"]; none when it is complete.
 */
export function missingFields(rule) {
  const minutes = (clock) => Number(clock.slice(0, 2)) * 60 + Number(clock.slice(3));
  return RULE_FIELDS[rule.ruleKind].filter((field) => {
    if (field === "days") return !rule.days?.length;
    if (field === "area") return !rule.area && !rule.task?.trim();
    if (!CLOCK.test(rule[field] || "")) return true;
    return field === "end" && CLOCK.test(rule.start || "") && minutes(rule.end) <= minutes(rule.start);
  });
}

/**
 * Name the fields a rule still needs, as a card says it.
 * @param {string[]} fields - From missingFields.
 * @param {(key: string, values?: object) => string} t - Interface text.
 * @param {string} language - `en` or `zh`.
 * @returns {string} Such as "a start time and its days".
 */
export function neededText(fields, t, language) {
  const named = fields.map((field) => t(NEEDED[field]));
  if (language === "zh") return named.join("、");
  return named.length > 1 ? `${named.slice(0, -1).join(", ")} and ${named.at(-1)}` : named[0] || "";
}
