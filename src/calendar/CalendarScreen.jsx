import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { fullDate } from "../time";
import { DayPanel } from "./DayPanel";
import { SummaryReports } from "./SummaryReports";
import { dayState } from "./dayState";
import { monthDates, monthTitle, shiftMonth } from "./month";

/**
 * One date in the month. It shows only what was recorded: a set plan and how much of it was
 * reported done, a recorded day without a plan, preset commitments ahead, and agent suggestions
 * still waiting. A past date is history; a date nobody recorded stays blank.
 * @param {object} props
 * @param {string} props.date - The YYYY-MM-DD date.
 * @param {object|undefined} props.record - Its record from the local service, if it has one.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.selected - Whether it is the day on show.
 * @param {(date: string) => void} props.onSelect - Show this day.
 */
function DayCell({ date, record, today, selected, onSelect }) {
  const { t, language } = useI18n();
  const state = dayState(record, date, today);
  const percent = state.total ? Math.round((state.done / state.total) * 100) : 0;
  const label = [
    fullDate(date, language),
    date === today && t("navToday"),
    state.set && t("cellSetOf", { done: state.done, total: state.total }),
    state.recorded && t("cellRecorded"),
    state.presets > 0 && t("cellPresets", { count: state.presets }),
    state.suggested > 0 && t("cellSuggested", { count: state.suggested }),
    state.empty && t("cellEmpty"),
    state.past && t("cellReadOnly"),
  ].filter(Boolean).join(t("clauseSeparator"));
  return (
    <button type="button" className={`dw-cal-day${state.past ? " dw-cal-past" : ""}${selected ? " dw-cal-selected" : ""}`}
      aria-label={label} aria-current={selected ? "date" : undefined} onClick={() => onSelect(date)}>
      <span className="dw-cal-head">
        <span className={`dw-cal-number${date === today ? " dw-cal-today" : ""}`}>{Number(date.slice(-2))}</span>
        {state.past && !state.empty && <Icon name="lock" size={14} />}
      </span>
      <span className="dw-cal-marks" aria-hidden="true">
        {state.set && (
          <>
            <span className="dw-cal-label"><Icon name="status-done" size={14} />{t("setChip")}</span>
            <span className="dw-cal-progress"><span className="dw-cal-bar"><span style={{ width: `${percent}%` }} /></span><span>{state.done}/{state.total}</span></span>
          </>
        )}
        {state.recorded && <span className="dw-cal-label"><Icon name="status-planned" size={14} />{t("cellRecordedShort")}</span>}
        {state.presets > 0 && <span className="dw-cal-label"><Icon name="pin" size={14} />{t("cellPresets", { count: state.presets })}</span>}
        {state.suggested > 0 && <span className="dw-chip dw-chip-dashed dw-chip-small"><Icon name="agent" size={14} />{t("cellSuggestedShort")}</span>}
      </span>
      <span className="dw-cal-dots" aria-hidden="true">
        {state.set && <span className="dw-mark-set" />}
        {state.recorded && <span className="dw-mark-recorded" />}
        {state.presets > 0 && <span className="dw-mark-preset" />}
        {state.suggested > 0 && <span className="dw-mark-suggested" />}
      </span>
    </button>
  );
}

/** What each mark in the month means. */
function Legend() {
  const { t } = useI18n();
  return (
    <ul className="dw-cal-legend">
      <li><span className="dw-mark-set" aria-hidden="true" /><Icon name="status-done" size={16} />{t("legendSet")}</li>
      <li><span className="dw-mark-recorded" aria-hidden="true" /><Icon name="status-planned" size={16} />{t("legendRecorded")}</li>
      <li><span className="dw-mark-preset" aria-hidden="true" /><Icon name="pin" size={16} />{t("legendPreset")}</li>
      <li><span className="dw-mark-suggested" aria-hidden="true" /><Icon name="agent" size={16} />{t("legendSuggested")}</li>
      <li><Icon name="lock" size={16} />{t("legendPast")}</li>
      <li><span className="dw-legend-empty" aria-hidden="true" />{t("legendEmpty")}</li>
    </ul>
  );
}

/**
 * The month of recorded days, past and future, beside the selected day and the Summary reports.
 * @param {object} props
 * @param {string} props.month - The YYYY-MM month on show.
 * @param {object[]} props.days - The month's records.
 * @param {object} props.day - The selected day.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {object|null} props.reports - Summary reports for the selected day's periods.
 * @param {object|null} props.pool - Saved advice for those periods.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(month: string) => void} props.onMonth - Show another month.
 * @param {(date: string) => void} props.onSelect - Show another day.
 * @param {() => void} props.onToday - Show today in the month.
 * @param {() => void} props.onOpenPlans - Show the selected day's plans.
 * @param {() => void} props.onOpenToday - Go to Today.
 * @param {() => void} props.onAddTask - Record a task on the selected day.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details.
 * @param {() => void} props.onAsk - Ask the agents about the selected day.
 * @param {(item: object, decision: "accept"|"dismiss") => Promise<void>} props.onDecide - Add or dismiss a suggestion.
 * @param {(adviceId: string) => void} props.onDismissAdvice - Stop an idea being used.
 * @param {(week: string, domain: string) => Promise<void>} props.onClearWeek - Delete a week's advice for one area.
 */
export function CalendarScreen({ month, days, day, today, reports, pool, backendConnected, onMonth, onSelect, onToday, onOpenPlans, onOpenToday, onAddTask, onOpenRow, onAsk, onDecide, onDismissAdvice, onClearWeek }) {
  const { t, language } = useI18n();
  const records = new Map(days.map((record) => [record.date, record]));
  const grid = monthDates(month);
  const lastOfMonth = grid.map((date) => date.slice(0, 7)).lastIndexOf(month);
  const dates = grid.slice(0, lastOfMonth - (lastOfMonth % 7) + 7);
  const title = monthTitle(month, language);
  const weekdays = dates.slice(0, 7).map((date) => new Intl.DateTimeFormat(language === "zh" ? "zh-Hans" : "en-GB", { weekday: "short" }).format(new Date(`${date}T12:00:00`)));

  return (
    <main className="dw-page" tabIndex={-1}>
      <header className="dw-cal-top">
        <h1 className="dw-display">{title}</h1>
        <div className="dw-actions">
          <button type="button" className="dw-button dw-icon-only" aria-label={t("previousMonth")} onClick={() => onMonth(shiftMonth(month, -1))}><Icon name="left" size={18} /></button>
          <button type="button" className="dw-button dw-icon-only" aria-label={t("nextMonth")} onClick={() => onMonth(shiftMonth(month, 1))}><Icon name="right" size={18} /></button>
          <button type="button" className="dw-button" onClick={onToday}>{t("navToday")}</button>
        </div>
      </header>
      <PageBanners day={day} backendConnected={backendConnected} />
      <div className="dw-columns">
        <section className="dw-card dw-cal-card" aria-label={t("monthGridLabel", { month: title })}>
          <div className="dw-cal-weekdays" aria-hidden="true">{weekdays.map((name) => <span key={name}>{name}</span>)}</div>
          <div className="dw-cal-grid">
            {dates.map((date) => date.slice(0, 7) === month
              ? <DayCell key={date} date={date} record={records.get(date)} today={today} selected={date === day.date} onSelect={onSelect} />
              : <span key={date} className="dw-cal-outside" aria-hidden="true">{Number(date.slice(-2))}</span>)}
          </div>
          <Legend />
        </section>
        <aside className="dw-column-side" aria-labelledby="dw-day-title">
          <DayPanel day={day} today={today} backendConnected={backendConnected} onOpenPlans={onOpenPlans} onOpenToday={onOpenToday}
            onAddTask={onAddTask} onOpenRow={onOpenRow} onAsk={onAsk} onDecide={onDecide} />
          <SummaryReports reports={reports} pool={pool} backendConnected={backendConnected}
            onDismissAdvice={onDismissAdvice} onClearWeek={onClearWeek} />
        </aside>
      </div>
    </main>
  );
}
