import { useEffect, useState } from "react";
import { api } from "../api";
import { GuideButton } from "../guide/Guide";
import { useI18n } from "../i18n";
import { AreaTag, DOMAINS } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { StatusControl } from "../ui/StatusControl";
import { AHEAD_DAYS, PAST_DAYS, taskDays, taskTimeCell } from "./taskList";
import { noReplyOf } from "./timeTaken";
import { fullDate } from "../time";
import { addDays } from "../calendar/month";

/** The area filter's choices: every area, then each one. */
const TASK_FILTERS = ["all", ...DOMAINS];

/**
 * One day's tasks, a group of the Tasks table under its date: each task's time, area, title, goal and status. Today's
 * and later tasks open their details, from anywhere on the row or by its title's button; past ones are history.
 * @param {object} props
 * @param {string} props.date - The YYYY-MM-DD date.
 * @param {object[]} props.items - The day's tasks.
 * @param {boolean} props.past - Whether the day has passed.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {Map<string, object>} props.goals - Goals by id, to name a linked one.
 * @param {number} props.columns - The table's columns, which the day's heading spans.
 * @param {boolean} props.hideArea - Leave out the Area column, in an area's own Tasks tab.
 * @param {(item: object) => void} props.onOpen - Show a task's details.
 */
function TaskDay({ date, items, past, today, goals, columns, hideArea, onOpen }) {
  const { t, language } = useI18n();
  return (
    <tbody role="rowgroup" aria-labelledby={`dw-tasks-${date}`}>
      <tr role="row" className="dw-task-day-row">
        <th id={`dw-tasks-${date}`} colSpan={columns} scope="rowgroup" role="rowheader" className="dw-task-day">{fullDate(date, language)}{past && <Icon name="lock" size={16} label={t("cellReadOnly")} />}</th>
      </tr>
      {items.map((item) => {
        const goal = goals.get(item.goalId);
        const cell = taskTimeCell(item, today, language);
        return (
          <tr key={item.id} role="row" className={past ? "dw-task-row" : "dw-task-row dw-task-row-open"} onClick={past ? undefined : () => onOpen(item)}>
            <td role="cell" className="dw-task-time">
              <span className="dw-task-range">{cell.range || t("untimed")}</span>
              <span className="dw-caption">{cell.length}</span>
              {cell.took && <span className="dw-caption dw-task-took">{t("taskTook", { length: cell.took })}</span>}
            </td>
            {!hideArea && <td role="cell" className="dw-task-area"><AreaTag domain={item.domain} /></td>}
            <td role="cell" className="dw-task-task">
              {past ? <span className="dw-task-title">{item.title}</span> : (
                <button type="button" className="dw-task-open" aria-label={`${item.title}, ${item.start_time || t("untimed")}, ${t(item.completion_status)}. ${t("openDetails")}`}
                  onClick={(event) => { event.stopPropagation(); onOpen(item); }}>{item.title}</button>
              )}
            </td>
            <td role="cell" className="dw-task-goal">{goal ? goal.title : <span className="dw-task-no-goal">{t("taskNoGoal")}</span>}</td>
            <td role="cell" className="dw-task-status"><StatusControl readOnly value={item.completion_status} noReply={noReplyOf(item)} /></td>
          </tr>
        );
      })}
    </tbody>
  );
}

/**
 * Every task across the last two weeks and the next two months, in one card, by date, in one area or all: the days
 * from today on, then the past days as history, under one row of column headings. Agent suggestions still waiting are
 * left to Calendar. The Tasks screen shows it under its area switch, and an area page's Tasks tab shows it for that
 * area alone, without the Area column.
 * @param {object} props
 * @param {object} props.day - The day on show; the list reloads whenever it does.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {string} props.area - "all", or the one area shown.
 * @param {boolean} [props.hideArea=false] - Leave out the Area column, where every task is in one area.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 */
export function TaskList({ day, today, backendConnected, area, hideArea = false, onOpenTask }) {
  const { t } = useI18n();
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

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
  const { shown, upcoming, past } = taskDays(items || [], area, today);
  const columns = hideArea ? 4 : 5;
  const group = (date, isPast) => (
    <TaskDay key={date} date={date} items={shown.filter((item) => item.date === date)} past={isPast} today={today} goals={goals}
      columns={columns} hideArea={hideArea} onOpen={onOpenTask} />
  );

  return (
    <>
      <p className="dw-muted dw-page-note">{t("tasksRangeNote", { past: PAST_DAYS, ahead: AHEAD_DAYS })}</p>
      {error && <p className="dw-alert" role="alert">{error}</p>}
      {!backendConnected && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("tasksNeedService")}</p>}
      {backendConnected && items && !shown.length && <p className="dw-banner dw-banner-history"><Icon name="info" size={18} />{t("noTasksInRange")}</p>}
      <div className="dw-page-body">
        {shown.length > 0 && (
          <section className="dw-card dw-task-list">
            <table className="dw-task-table" role="table" aria-label={t("tasksTitle")}>
              <thead role="rowgroup">
                <tr role="row">
                  <th scope="col" role="columnheader" className="dw-col-time">{t("taskColTime")}</th>
                  {!hideArea && <th scope="col" role="columnheader" className="dw-col-area">{t("taskColArea")}</th>}
                  <th scope="col" role="columnheader" className="dw-col-task">{t("taskColTask")}</th>
                  <th scope="col" role="columnheader" className="dw-col-goal">{t("taskColGoal")}</th>
                  <th scope="col" role="columnheader" className="dw-col-status">{t("taskColStatus")}</th>
                </tr>
              </thead>
              {upcoming.map((date) => group(date, false))}
              {past.length > 0 && (
                <tbody role="rowgroup">
                  <tr role="row" className="dw-task-past-row">
                    <td role="cell" colSpan={columns}><h2 className="dw-section-label dw-tasks-past">{t("pastDaysHeading", { count: PAST_DAYS })}</h2></td>
                  </tr>
                </tbody>
              )}
              {past.map((date) => group(date, true))}
            </table>
          </section>
        )}
      </div>
    </>
  );
}

/**
 * Every task across the last two weeks and the next two months, by date, filtered by area (see TaskList).
 * @param {object} props
 * @param {object} props.day - The day on show; the list reloads whenever it does.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {() => void} props.onAddTask - Record a task today.
 * @param {string} [props.initialArea="all"] - The area the list opens filtered to, as a reminder's See tasks sets it.
 * @param {(screen: string) => void} props.onGuide - Open Tasks' cards from the Guide.
 * @param {() => void} props.onCatchUp - Catch up on today's tasks at once, in a sheet.
 */
export function TasksScreen({ day, today, backendConnected, onOpenTask, onAddTask, initialArea = "all", onGuide, onCatchUp }) {
  const { t } = useI18n();
  const [area, setArea] = useState(initialArea);

  return (
    <main className="dw-page" tabIndex={-1}>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <div className="dw-title-guide">
            <h1 className="dw-display">{t("tasksTitle")}</h1>
            <GuideButton screen="tasks" onFullGuide={onGuide} />
          </div>
          <Segmented label={t("fieldArea")} value={area} onChange={setArea}
            options={TASK_FILTERS.map((value) => [value, value === "all" ? t("filterAll") : <AreaTag key={value} domain={value} plain />])} />
        </div>
        <div className="dw-page-actions">
          <button type="button" className="dw-button" disabled={!backendConnected} onClick={onCatchUp}><Icon name="check" size={18} />{t("catchUpAction")}</button>
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addTaskAction")}</button>
        </div>
      </header>
      <PageBanners day={day} backendConnected={backendConnected} />
      <TaskList day={day} today={today} backendConnected={backendConnected} area={area} onOpenTask={onOpenTask} />
    </main>
  );
}
