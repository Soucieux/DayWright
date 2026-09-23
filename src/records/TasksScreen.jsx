import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaGlyph, AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { StatusControl } from "../ui/StatusControl";
import { fullDate } from "../time";
import { addDays } from "../calendar/month";

/** Days back the list reaches; those days are history. */
const PAST_DAYS = 14;

/** Days ahead the list reaches. */
const AHEAD_DAYS = 60;

/** The area filter's choices: every area, then each one. */
const TASK_FILTERS = ["all", "learning", "life", "finance", "rest"];

/**
 * One day's tasks under its date. Today's and later tasks open their details; past ones are history.
 * @param {object} props
 * @param {string} props.date - The YYYY-MM-DD date.
 * @param {object[]} props.items - The day's tasks.
 * @param {boolean} props.past - Whether the day has passed.
 * @param {Map<string, object>} props.goals - Goals by id, to name a linked one.
 * @param {(item: object) => void} props.onOpen - Show a task's details.
 */
function TaskDay({ date, items, past, goals, onOpen }) {
  const { t, language, demoText } = useI18n();
  return (
    <section className="dw-card" aria-labelledby={`dw-tasks-${date}`}>
      <h2 id={`dw-tasks-${date}`} className="dw-heading dw-card-title">{fullDate(date, language)}{past && <Icon name="lock" size={16} label={t("cellReadOnly")} />}</h2>
      <ul className="dw-day-rows">
        {items.map((item) => {
          const goal = goals.get(item.goalId);
          const content = (
            <>
              <span className="dw-plan-time">{item.start_time}</span>
              <AreaGlyph domain={item.domain} />
              <span className="dw-day-row-title">{demoText(item.title)}
                {goal && <span className="dw-caption"><Icon name="link" size={14} /> {demoText(goal.title)}</span>}</span>
              <StatusControl readOnly value={item.completion_status} />
            </>
          );
          return (
            <li key={item.id}>
              {past ? <div className="dw-day-row">{content}</div> : (
                <button type="button" className="dw-day-row" aria-label={`${demoText(item.title)}, ${item.start_time}, ${t(item.completion_status)}. ${t("openDetails")}`} onClick={() => onOpen(item)}>
                  {content}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/**
 * Every task across the last two weeks and the next two months, by date, filtered by area or by
 * the goal they are linked to. Agent suggestions still waiting are left to Calendar.
 * @param {object} props
 * @param {object} props.day - The day on show; the list reloads whenever it does.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {object|null} props.goal - A goal whose linked tasks alone are shown, or null.
 * @param {() => void} props.onClearGoal - Show every task again.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {() => void} props.onAddTask - Record a task today.
 */
export function TasksScreen({ day, today, backendConnected, goal, onClearGoal, onOpenTask, onAddTask }) {
  const { t, demoText } = useI18n();
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [area, setArea] = useState("all");

  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    const query = new URLSearchParams({ start: addDays(today, -PAST_DAYS), end: addDays(today, AHEAD_DAYS) });
    api(`/api/daily-items?${query}`)
      .then((result) => { if (live) { setItems(result.items); setError(""); } })
      .catch((caught) => live && setError(caught.message));
    return () => { live = false; };
  }, [day, today, backendConnected]);

  const goals = new Map(day.goals.map((entry) => [entry.id, entry]));
  const shown = (items || [])
    .filter((item) => item.acceptance !== "pending")
    .filter((item) => area === "all" || item.domain === area)
    .filter((item) => !goal || item.goalId === goal.id);
  const dates = [...new Set(shown.map((item) => item.date))];
  const upcoming = dates.filter((date) => date >= today);
  const past = dates.filter((date) => date < today).reverse();
  const group = (date, isPast) => (
    <TaskDay key={date} date={date} items={shown.filter((item) => item.date === date)} past={isPast} goals={goals} onOpen={onOpenTask} />
  );

  return (
    <main className="dw-page" tabIndex={-1}>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <h1 className="dw-display">{t("tasksTitle")}</h1>
          <Segmented label={t("fieldArea")} value={area} onChange={setArea}
            options={TASK_FILTERS.map((value) => [value, value === "all" ? t("filterAll") : <AreaTag key={value} domain={value} plain />])} />
        </div>
        <div className="dw-page-actions">
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addTaskAction")}</button>
        </div>
      </header>
      <PageBanners day={day} backendConnected={backendConnected} />
      <p className="dw-muted dw-page-note">{t("tasksRangeNote", { past: PAST_DAYS, ahead: AHEAD_DAYS })}</p>
      {goal && (
        <p className="dw-chips dw-tasks-filter">
          <span className="dw-chip"><Icon name="link" size={14} />{t("linkedToGoal", { title: demoText(goal.title) })}</span>
          <button type="button" className="dw-link" onClick={onClearGoal}>{t("showAllTasks")}</button>
        </p>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
      {!backendConnected && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("tasksNeedService")}</p>}
      {backendConnected && items && !shown.length && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("noTasksInRange")}</p>}
      {upcoming.length > 0 && <div className="dw-task-days">{upcoming.map((date) => group(date, false))}</div>}
      {past.length > 0 && (
        <>
          <h2 className="dw-section-label dw-tasks-past">{t("pastDaysHeading", { count: PAST_DAYS })}</h2>
          <div className="dw-task-days">{past.map((date) => group(date, true))}</div>
        </>
      )}
    </main>
  );
}
