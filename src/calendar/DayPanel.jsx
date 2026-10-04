import { useI18n } from "../i18n";
import { AreaGlyph, DOMAINS, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { StatusControl } from "../ui/StatusControl";
import { TimeColumn } from "../ui/TimeColumn";
import { SuggestionCard } from "../records/SuggestionCard";
import { planName } from "../plans/planName";
import { dayRows } from "../today/dayRows";
import { clockOfTimestamp, formatMinutes, longDate } from "../time";
import { daysBetween } from "./month";

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
 * The day's plan at a glance: which plan was set, or used on a past day, how its entries were
 * reported, its time by area, and the day's actions under them.
 * @param {object} props
 * @param {object} props.day - The selected day.
 * @param {object[]} props.entries - The set plan's entries.
 * @param {boolean} props.past - Whether the day has passed.
 * @param {React.ReactNode} props.actions - The day's buttons, at the foot of the card.
 */
function PlanSummary({ day, entries, past, actions }) {
  const { t, language, demoText } = useI18n();
  const setVariant = day.variants.find((variant) => variant.id === day.confirmedVariantId);
  const minutesIn = (domain) => entries.filter((entry) => entry.domain === domain).reduce((total, entry) => total + entry.duration_minutes, 0);
  const areas = DOMAINS.filter((domain) => minutesIn(domain));
  const setAt = clockOfTimestamp(day.confirmedAt);
  if (!setVariant) {
    return (
      <section className="dw-card"><span className="dw-chip dw-chip-dashed"><Icon name="pencil" size={14} />{day.variants.length} {t("draftsNotSet")}</span>
        {actions}</section>
    );
  }
  const chip = past ? t("planUsedChip") : t("planSetChip");
  return (
    <section className="dw-card" aria-label={chip}>
      <span className="dw-chip dw-chip-ink"><Icon name="check" size={14} />{chip} · {planName(setVariant, t, demoText)}{setAt && ` · ${setAt}`}</span>
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
      {actions}
    </section>
  );
}

/**
 * One row of the day's schedule: time, area, title and status, or Paused for a task paused with its
 * goal, and Removed for a past plan's entry whose task was removed. On a past day it is history and
 * opens nothing; otherwise it opens the task's details.
 * @param {object} props
 * @param {object} props.row - The task or plan entry.
 * @param {boolean} props.past - Whether the day has passed.
 * @param {(row: object) => void} props.onOpen - Show the row's details.
 */
function DayRow({ row, past, onOpen }) {
  const { t, demoText } = useI18n();
  // A past day is history; on any other, a task paused with its goal shows Paused, not its status.
  const paused = !past && row.source?.goalStatus === "paused";
  const content = (
    <>
      <TimeColumn row={row} />
      <AreaGlyph domain={row.domain} />
      <span className="dw-day-row-title">{demoText(row.title)}
        {row.source?.originKind === "agent-origin" && <span className="dw-caption">{t("agentAccepted")}</span>}
        {row.removed && <span className="dw-chip dw-chip-small dw-chip-history">{t("entryRemoved")}</span>}</span>
      <StatusControl readOnly value={row.completion_status} paused={paused} />
    </>
  );
  if (past) return <div className="dw-day-row">{content}</div>;
  return (
    <button type="button" className="dw-day-row" aria-label={`${demoText(row.title)}, ${row.start_time || t("noStartTime")}, ${t(paused ? "paused" : row.completion_status)}. ${t("openDetails")}`} onClick={() => onOpen(row)}>
      {content}
    </button>
  );
}

/**
 * The selected day beside the month: whether it can change, its plan, its schedule as reported,
 * and any agent suggestions waiting for the user. A past day is read-only here: it names the plan
 * it followed, and says that a task is changed or removed by asking Ava; a day nobody recorded
 * says so instead of being filled in.
 * @param {object} props
 * @param {object} props.day - The selected day.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onOpenPlans - Show the day's plans.
 * @param {() => void} props.onAddTask - Record a task on this day.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details.
 * @param {() => void} props.onAsk - Ask the agents about this day.
 * @param {(item: object, decision: "accept"|"dismiss") => Promise<void>} props.onDecide - Add or dismiss a suggestion.
 */
export function DayPanel({ day, today, backendConnected, onOpenPlans, onAddTask, onOpenRow, onAsk, onDecide }) {
  const { t, language } = useI18n();
  const past = day.date < today;
  const offset = daysBetween(today, day.date);
  const { weekday, dayMonth } = longDate(day.date, language);
  const { rows, timed, untimed, fromPlan, suggestions } = dayRows(day);
  const empty = !rows.length && !day.planSetId && !suggestions.length;
  // The day's buttons sit under its counts, in the plan's card, when the day has plans.
  const actions = (
    <div className="dw-actions dw-day-actions">
      {day.planSetId && <button type="button" className="dw-button" onClick={onOpenPlans}><Icon name="eye" size={18} />{past ? t("openFullDay") : t("openPlansAction")}</button>}
      <button type="button" className="dw-button" disabled={!backendConnected} onClick={onAsk}><Icon name="talk" size={18} />{t("askAboutDay")}</button>
    </div>
  );

  return (
    <>
      <header className="dw-day-head">
        <div>
          <p className="dw-eyebrow">{weekday} · {relativeDay(offset, t)}</p>
          <h2 className="dw-title">{dayMonth}</h2>
        </div>
        {!past && <button type="button" className="dw-button" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addAction")}</button>}
      </header>
      {past && (
        <p className="dw-banner dw-banner-history dw-banner-titled" role="note"><Icon name="lock" size={18} />
          <span className="dw-banner-text"><span><strong>{t("readOnlyPastDay")}</strong> · {t("readOnlyPastBody")}</span>
            {!day.confirmedVariantId && <span>{t("pastDayNoPlan")}</span>}
            <span className="dw-caption">{t("pastDayAskAva")}</span></span></p>
      )}
      {offset > 0 && !day.planSetId && !empty && <p className="dw-muted">{t("futureNoPlanNote")}</p>}
      {day.planSetId && <PlanSummary day={day} entries={rows.filter((row) => row.kind === "entry")} past={past} actions={actions} />}
      {timed.length > 0 && (
        <section className="dw-card" aria-labelledby="dw-day-schedule">
          <div className="dw-card-head">
            <h3 id="dw-day-schedule" className="dw-heading">{t("scheduleTitle")}</h3>
            <span className="dw-caption">{past ? t("asReported") : `${timed.length} ${fromPlan ? t("entriesCount") : t("tasksCount")}`}</span>
          </div>
          <ul className="dw-day-rows">
            {timed.map((row) => <li key={`${row.kind}-${row.id}`}><DayRow row={row} past={past} onOpen={onOpenRow} /></li>)}
          </ul>
        </section>
      )}
      {untimed.length > 0 && (
        <section className="dw-card dw-untimed" aria-labelledby="dw-day-untimed">
          <div className="dw-card-head">
            <h3 id="dw-day-untimed" className="dw-heading">{t("noStartTime")}</h3>
            <span className="dw-caption">{untimed.length} {t("tasksCount")}</span>
          </div>
          <p className="dw-caption">{t("noStartTimeNote")}</p>
          <ul className="dw-day-rows">
            {untimed.map((row) => <li key={`${row.kind}-${row.id}`}><DayRow row={row} past={past} onOpen={onOpenRow} /></li>)}
          </ul>
        </section>
      )}
      {suggestions.map((item) => <SuggestionCard key={item.id} item={item} backendConnected={backendConnected} onDecide={onDecide} />)}
      {empty && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{past ? t("dayEmptyPast") : t("dayEmptyFuture")}</p>}
      {!day.planSetId && actions}
    </>
  );
}
