import { useI18n } from "../i18n";
import { AreaGlyph, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { StatusControl } from "../ui/StatusControl";
import { SuggestionCard } from "../records/SuggestionCard";
import { planName } from "../plans/planName";
import { dayRows } from "../today/dayRows";
import { clockOfTimestamp, formatMinutes, longDate } from "../time";
import { daysBetween } from "./month";

/** Areas in the order a plan's time is summed. */
const PANEL_AREAS = ["learning", "life", "finance", "rest"];

/** Reported states in the order the plan's tallies show them; planned counts as unreported. */
const TALLIES = [["done", "done"], ["partial", "partial"], ["skipped", "skipped"], ["planned", "statusUnreported"]];

/**
 * Say how far a date is from today, in words.
 * @param {number} offset - Days from today; negative for the past.
 * @param {(key: string, values?: object) => string} t - The interface text lookup.
 * @returns {string} Such as "Today", "Tomorrow" or "In 2 days".
 */
function relativeDay(offset, t) {
  if (offset === 0) return t("navToday");
  if (offset === 1) return t("tomorrow");
  if (offset === -1) return t("yesterday");
  return offset > 0 ? t("inDays", { count: offset }) : t("daysAgo", { count: -offset });
}

/**
 * The day's plan at a glance: which plan was set, how its entries were reported, and its time by area.
 * @param {object} props
 * @param {object} props.day - The selected day.
 * @param {object[]} props.entries - The set plan's entries.
 */
function PlanSummary({ day, entries }) {
  const { t, language, demoText } = useI18n();
  const setVariant = day.variants.find((variant) => variant.id === day.confirmedVariantId);
  const minutesIn = (domain) => entries.filter((entry) => entry.domain === domain).reduce((total, entry) => total + entry.duration_minutes, 0);
  const areas = PANEL_AREAS.filter((domain) => minutesIn(domain));
  const setAt = clockOfTimestamp(day.confirmedAt);
  if (!setVariant) {
    return <section className="dw-card"><span className="dw-chip dw-chip-dashed"><Icon name="pencil" size={14} />{day.variants.length} {t("draftsNotSet")}</span></section>;
  }
  return (
    <section className="dw-card" aria-label={t("planSetChip")}>
      <span className="dw-chip dw-chip-ink"><Icon name="check" size={14} />{t("planSetChip")} · {planName(setVariant, t, demoText)}{setAt && ` · ${setAt}`}</span>
      <ul className="dw-day-tallies">
        {TALLIES.map(([status, key]) => (
          <li key={status}><strong>{entries.filter((entry) => entry.completion_status === status).length}</strong>
            <span><Icon name={`status-${status}`} size={14} />{t(key)}</span></li>
        ))}
      </ul>
      <div className="dw-stack" aria-hidden="true">
        {areas.map((domain) => <span key={domain} className={`dw-area-${areaOf(domain)}`} style={{ flexGrow: minutesIn(domain) }} />)}
      </div>
      <p className="dw-caption">{areas.map((domain) => `${t(domain)} ${formatMinutes(minutesIn(domain), language)}`).join(" · ")}</p>
    </section>
  );
}

/**
 * One row of the day's schedule: time, area, title and status. On a past day it is history and
 * opens nothing; otherwise it opens the task's details.
 * @param {object} props
 * @param {object} props.row - The task or plan entry.
 * @param {boolean} props.past - Whether the day has passed.
 * @param {(row: object) => void} props.onOpen - Show the row's details.
 */
function DayRow({ row, past, onOpen }) {
  const { t, demoText } = useI18n();
  const content = (
    <>
      <span className="dw-plan-time">{row.start_time}</span>
      <AreaGlyph domain={row.domain} />
      <span className="dw-day-row-title">{demoText(row.title)}
        {row.source?.originKind === "agent-origin" && <span className="dw-caption">{t("agentAccepted")}</span>}</span>
      <StatusControl readOnly value={row.completion_status} />
    </>
  );
  if (past) return <div className="dw-day-row">{content}</div>;
  return (
    <button type="button" className="dw-day-row" aria-label={`${demoText(row.title)}, ${row.start_time}, ${t(row.completion_status)}. ${t("openDetails")}`} onClick={() => onOpen(row)}>
      {content}
    </button>
  );
}

/**
 * The selected day beside the month: whether it can change, its plan, its schedule as reported,
 * and any agent suggestions waiting for the user. A past day is read-only; a day nobody recorded
 * says so instead of being filled in.
 * @param {object} props
 * @param {object} props.day - The selected day.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onOpenPlans - Show the day's plans.
 * @param {() => void} props.onOpenToday - Go to Today.
 * @param {() => void} props.onAddTask - Record a task on this day.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details.
 * @param {() => void} props.onAsk - Ask the agents about this day.
 * @param {(item: object, decision: "accept"|"dismiss") => Promise<void>} props.onDecide - Add or dismiss a suggestion.
 */
export function DayPanel({ day, today, backendConnected, onOpenPlans, onOpenToday, onAddTask, onOpenRow, onAsk, onDecide }) {
  const { t, language } = useI18n();
  const past = day.date < today;
  const offset = daysBetween(today, day.date);
  const { weekday, dayMonth } = longDate(day.date, language);
  const { rows, fromPlan, suggestions } = dayRows(day);
  const empty = !rows.length && !day.planSetId && !suggestions.length;

  return (
    <>
      <header className="dw-day-head">
        <div>
          <p className="dw-eyebrow">{weekday} · {relativeDay(offset, t)}</p>
          <h2 id="dw-day-title" className="dw-title">{dayMonth}</h2>
        </div>
        {!past && <button type="button" className="dw-button" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addAction")}</button>}
      </header>
      {past && <p className="dw-banner dw-banner-history" role="note"><Icon name="lock" size={18} /><span><strong>{t("readOnlyPastDay")}</strong> · {t("readOnlyPastBody")}</span></p>}
      {offset > 0 && !day.planSetId && !empty && <p className="dw-muted">{t("futureNoPlanNote")}</p>}
      {day.planSetId && <PlanSummary day={day} entries={rows.filter((row) => row.kind === "entry")} />}
      {rows.length > 0 && (
        <section className="dw-card" aria-labelledby="dw-day-schedule">
          <div className="dw-card-head">
            <h3 id="dw-day-schedule" className="dw-heading">{t("scheduleTitle")}</h3>
            <span className="dw-caption">{past ? t("asReported") : `${rows.length} ${fromPlan ? t("entriesCount") : t("tasksCount")}`}</span>
          </div>
          <ul className="dw-day-rows">
            {rows.map((row) => <li key={`${row.kind}-${row.id}`}><DayRow row={row} past={past} onOpen={onOpenRow} /></li>)}
          </ul>
        </section>
      )}
      {suggestions.map((item) => <SuggestionCard key={item.id} item={item} backendConnected={backendConnected} onDecide={onDecide} />)}
      {empty && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{past ? t("dayEmptyPast") : t("dayEmptyFuture")}</p>}
      <div className="dw-actions">
        {offset === 0
          ? <button type="button" className="dw-button" onClick={onOpenToday}><Icon name="sun" size={18} />{t("openTodayAction")}</button>
          : day.planSetId && <button type="button" className="dw-button" onClick={onOpenPlans}><Icon name="eye" size={18} />{past ? t("openFullDay") : t("openPlansAction")}</button>}
        <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={onAsk}><Icon name="talk" size={18} />{t("askAboutDay")}</button>
      </div>
    </>
  );
}
