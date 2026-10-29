import { useEffect, useState } from "react";
import { GuideButton } from "../guide/Guide";
import { useI18n } from "../i18n";
import { AreaTag, DOMAINS, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { FinishingCard } from "../ui/ProgressGraphs";
import { Segmented } from "../ui/Segmented";
import { SideTabs } from "../ui/SideTabs";
import { StatusControl } from "../ui/StatusControl";
import { noReplyOf, spentMinutes, timeTaken, totalMinutes, yesterdayLines } from "../records/timeTaken";
import { TimeColumn } from "../ui/TimeColumn";
import { latestReading } from "../ui/visuals";
import { MINUTE_MS, clockOf, formatMinutes, longDate, minutesOf, nowMinutes, timeRange } from "../time";
import { SummaryReports } from "../calendar/SummaryReports";
import { DayStrip } from "./DayStrip";
import { SuggestionCard } from "../records/SuggestionCard";
import { taskLength } from "../records/taskDraft";
import { AvaOnly } from "../settings/NeedsModel";
import { openSettings } from "../settings/models";
import { holidayName } from "../settings/schedule";
import { dayRows } from "./dayRows";
import { ModelCard } from "./ModelCard";
import { PlanSection } from "./PlanSection";
import { REMINDER_ACTIONS, REMINDERS_SHOWN, reminderLine } from "./reminders";

/** The levels an energy reading takes, lowest first. */
const ENERGY_LEVELS = ["1", "2", "3", "4", "5"];

/**
 * Minutes after midnight, renewed as each minute turns, so the day strip, the next task and the
 * open time keep up in an app left open.
 * @returns {number} Minutes after midnight now.
 */
function useNowMinutes() {
  const [now, setNow] = useState(nowMinutes);
  useEffect(() => {
    let timer;
    /** Move the clock on, then wait for the next minute to begin. */
    const tick = () => {
      setNow(nowMinutes());
      timer = setTimeout(tick, MINUTE_MS - (Date.now() % MINUTE_MS));
    };
    timer = setTimeout(tick, MINUTE_MS - (Date.now() % MINUTE_MS));
    return () => clearTimeout(timer);
  }, []);
  return now;
}

/**
 * Whether a row's task is paused with its goal, so it can be neither the next action nor reported.
 * @param {object} row - A row from dayRows, with its source task.
 * @returns {boolean} True when the task's goal is paused.
 */
const isPaused = (row) => row.source?.goalStatus === "paused";

/**
 * The workbench for today: one schedule, the next action, and the few facts that describe the day.
 * Beside them, tabs hold the day's details, today's plan with what it changed and why, and the
 * Summary agent's report on today.
 * @param {object} props
 * @param {object} props.day - Today's records, plan and model state.
 * @param {object|null} props.reports - Summary reports for today's periods.
 * @param {object|null} props.pool - Saved Summary advice by period.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details, with Edit and Remove.
 * @param {boolean} props.proposing - Whether the agents are proposing plans now.
 * @param {() => void} props.onPropose - Ask the agents for alternatives.
 * @param {() => void} props.onPlans - Open the plan comparison.
 * @param {() => void} props.onDeselect - Stop following the set plan, keeping its proposals.
 * @param {() => void} props.onGoals - Open goals in Records.
 * @param {() => void} props.onAddTask - Record a new task.
 * @param {() => void} props.onReplace - Ask for a replacement of the set plan.
 * @param {(adviceId: string) => void} props.onDismissAdvice - Stop an idea being dispatched.
 * @param {(item: object, decision: "accept"|"dismiss") => Promise<void>} props.onDecide -
 *   Add or dismiss an agent's suggestion.
 * @param {(level: number) => void} props.onEnergy - Report today's energy, 1 to 5.
 * @param {(screen: string) => void} props.onGuide - Open Today's cards from the Guide.
 * @param {(text: string) => void} props.onAskAva - Open Ava with a request ready to send.
 * @param {(date: string) => void} props.onDismissYesterday - Hide the notice about what yesterday left to fix.
 * @param {(ids: string[]) => void} props.onDismissReminders - Dismiss reminders, by their ids.
 * @param {(area: string) => void} props.onSeeTasks - Show an area's tasks.
 * @param {(goal: {domain: string, goalId: string}) => void} props.onAddStep - Add a task to a goal.
 * @param {() => void} props.onPause - Pause today: nothing is current and no time counts until Resume or Your day's end.
 * @param {() => void} props.onResume - Resume the paused day.
 * @param {() => void} props.onCatchUp - Catch up on today's tasks at once, in a sheet.
 */
export function TodayScreen({ day, reports, pool, backendConnected, proposing, onStatus, onOpenRow, onPropose, onPlans, onDeselect, onGoals, onAddTask, onReplace, onDismissAdvice, onDecide, onEnergy, onGuide, onAskAva, onDismissYesterday, onDismissReminders, onSeeTasks, onAddStep, onCatchUp, onPause, onResume }) {
  const { t, language } = useI18n();
  const { weekday, dayMonth } = longDate(day.date, language);
  const { rows, timed, untimed, fromPlan, suggestions, meals } = dayRows(day);
  const reminders = day.reminders || [];
  const drafts = !fromPlan && day.planSetId ? day.variants.length : 0;
  const empty = !rows.length && !day.planSetId;
  const now = useNowMinutes();
  /** Whether a row is still to do: planned or partly done, and not paused. */
  const unfinished = (row) => !isPaused(row) && (row.completion_status === "planned" || row.completion_status === "partial");
  // The next timed task still to come; once none is left today, the first task without a start time.
  const next = timed.filter(unfinished).find((row) => minutesOf(row.start_time) + row.duration_minutes > now)
    || untimed.find(unfinished) || null;
  const reported = rows.filter((row) => row.completion_status !== "planned");
  // Time spent counts the time every reported task took, whatever its status.
  const reportedMinutes = totalMinutes(rows, spentMinutes);
  const plannedMinutes = totalMinutes(rows);

  return (
    <main className="dw-page dw-today" tabIndex={-1}>
      <header className="dw-page-head dw-today-head">
        <div className="dw-today-date">
          <p className="dw-eyebrow">{weekday}</p>
          <div className="dw-title-guide">
            <h1 className="dw-display">{dayMonth}</h1>
            <GuideButton screen="today" onFullGuide={onGuide} />
          </div>
          <div className="dw-chips">
            {rows.length > 0 && <span className="dw-chip"><Icon name="check" size={14} />{t("reportedChip")} {reported.length} / {rows.length} · {formatMinutes(reportedMinutes, language)} / {formatMinutes(plannedMinutes, language)}</span>}
            {empty && <span className="dw-chip"><Icon name="info" size={14} />{t("nothingRecordedToday")}</span>}
            {day.pausedSince && <span className="dw-chip dw-chip-paused"><Icon name="pause" size={14} />{t("pausedSinceChip", { time: day.pausedSince })}</span>}
            {day.holiday && <span className="dw-chip dw-chip-holiday"><Icon name="calendar" size={14} />{t("holidayChip", { name: holidayName(day.holiday, language) })}</span>}
          </div>
        </div>
        <DayStrip timed={timed} next={next} now={now} dayMeals={day.meals || []} day={day.yourDay} empty={empty} />
        {/* The energy row sits above the day's buttons, and alone in their place on a day with no tasks. */}
        <div className="dw-today-actions">
          <EnergyRow level={latestReading(day.energyReadings)} backendConnected={backendConnected} onEnergy={onEnergy} />
          {!empty && (
            <div className="dw-page-actions">
              {rows.length > 0 && (
                <button type="button" className="dw-button" disabled={!backendConnected} onClick={onCatchUp}><Icon name="check" size={18} />{t("catchUpAction")}</button>
              )}
              {day.pausedSince
                ? <button type="button" className="dw-button" disabled={!backendConnected} onClick={onResume}><Icon name="arrow" size={18} /><PauseLabel shown="resumeDayAction" /></button>
                : <button type="button" className="dw-button" disabled={!backendConnected} onClick={onPause}><Icon name="pause" size={18} /><PauseLabel shown="pauseDayAction" /></button>}
              <button type="button" className="dw-button" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addTaskAction")}</button>
              {!fromPlan && (drafts > 0
                ? <button type="button" className="dw-button dw-button-primary" onClick={onPlans}>{t("compareAndSet")}</button>
                : <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected || proposing} aria-busy={proposing}
                  onClick={onPropose}><Icon name="agent" size={18} />{t(proposing ? "proposingAction" : "proposePlansAction")}</button>)}
            </div>
          )}
        </div>
      </header>

      <PageBanners day={day} backendConnected={backendConnected} />
      {(day.yesterdayNotice || reminders.length > 0 || day.holidayReminder) && <TodayNotices day={day} yesterday={day.yesterdayNotice} reminders={reminders}
        rows={rows} backendConnected={backendConnected} onAskAva={onAskAva} onDismissYesterday={onDismissYesterday}
        onDismissReminders={onDismissReminders} onOpenRow={onOpenRow} onPlans={onPlans} onSeeTasks={onSeeTasks} onAddStep={onAddStep} />}

      <div className="dw-columns dw-page-body">
        <div className="dw-column-main">
          {suggestions.map((item) => <SuggestionCard key={item.id} item={item} backendConnected={backendConnected} onDecide={onDecide} />)}
          {empty
            ? <EmptyToday backendConnected={backendConnected} onGoals={onGoals} onAddTask={onAddTask} />
            : timed.length > 0 && <Schedule rows={timed} meals={meals} next={next} now={now} backendConnected={backendConnected} onStatus={onStatus} onOpen={onOpenRow} />}
          {untimed.length > 0 && <UntimedTasks rows={untimed} next={next} backendConnected={backendConnected} onStatus={onStatus} onOpen={onOpenRow} />}
        </div>
        <aside className="dw-column-side">
          <SideTabs label={t("aboutTheDay")} tabs={[
            ["day", t("dayDetailsTab"), (
              <>
                {backendConnected && day.model?.state === "unavailable" && <ModelCard model={day.model} />}
                {next && <NextCard row={next} now={now} goals={day.goals} backendConnected={backendConnected} onStatus={onStatus} />}
                <BalanceCard rows={rows} />
                {day.finishingWeek && <FinishingCard days={day.finishingWeek} date={day.date} />}
              </>
            )],
            ["plan", t("planTab"), <PlanSection day={day} fromPlan={fromPlan} backendConnected={backendConnected}
              onPlans={onPlans} onReplace={onReplace} onDeselect={onDeselect} />],
            ["summary", t("summaryAgent"), <SummaryReports reports={reports} pool={pool} backendConnected={backendConnected} dayOnly
              yourDay={day.yourDay}
              onDismissAdvice={onDismissAdvice} />],
          ]} />
        </aside>
      </div>
    </main>
  );
}

/**
 * What yesterday left to fix, on Today until the user dismisses it: each task left without a status,
 * stopped at its limit without one, or with a time to check, and when the day was paused if it ended
 * paused. A past day changes only through Ava, so its button asks Ava to catch up on yesterday: her card
 * lists every task of yesterday's to set at once; or, when the notice holds only times to check, to check
 * them, each Right or Change. Not catching up never stops any of them being carried forward.
 * @param {object} props
 * @param {{date: string, tasks: object[]}} props.notice - Yesterday's tasks to fix, from the local service.
 * @param {boolean} props.backendConnected - Whether Ava can change anything.
 * @param {(text: string, send: boolean) => void} props.onAskAva - Open Ava with a request, sent at once.
 * @param {(date: string) => void} props.onDismiss - Hide the notice.
 */
function YesterdayNotice({ notice, backendConnected, onAskAva, onDismiss }) {
  const { t } = useI18n();
  const { title, paused, tasks, onlyTimes } = yesterdayLines(notice, t);
  return (
    <section className="dw-notice-group dw-yesterday" aria-labelledby="dw-yesterday-title">
      <Icon name="history" size={18} />
      <div className="dw-banner-text">
        <h2 id="dw-yesterday-title" className="dw-label">{title}</h2>
        {paused && <p className="dw-caption">{paused}</p>}
        <ul className="dw-yesterday-tasks">{tasks.map((line, index) => <li key={notice.tasks[index].id}>{line}</li>)}</ul>
      </div>
      <div className="dw-actions">
        {/* Yesterday changes only through Ava: while she can't answer, the notice says she needs a model instead. */}
        <AvaOnly>
          <button type="button" className="dw-button" disabled={!backendConnected}
            onClick={() => onAskAva(onlyTimes ? t("checkTimesPrompt") : t("catchUpYesterdayPrompt"), true)}>
            {t(onlyTimes ? "checkTimesAction" : "yesterdayAskAva")}</button>
        </AvaOnly>
        <button type="button" className="dw-button dw-button-quiet" onClick={() => onDismiss(notice.date)}>{t("dismissAction")}</button>
      </div>
    </section>
  );
}

/**
 * Pause's or Resume's label, holding the room of the wider of the two, so swapping them never widens the header's actions
 * and narrows the day strip beside them; the other label takes its room unseen and unread.
 * @param {object} props
 * @param {"pauseDayAction"|"resumeDayAction"} props.shown - The label shown.
 */
function PauseLabel({ shown }) {
  const { t } = useI18n();
  return (
    <span className="dw-pause-label">
      {["pauseDayAction", "resumeDayAction"].map((key) => (
        <span key={key} className={key === shown ? undefined : "dw-pause-room"} aria-hidden={key === shown ? undefined : "true"}>{t(key)}</span>
      ))}
    </span>
  );
}

/**
 * Today's notice box: yesterday's tasks to fix (see YesterdayNotice), then, under a thin divider when both show, the
 * reminders the agents raised about today, "Reminders · N". Each reminder is one line: its area, its short form, its
 * age, the one thing to do about it and Dismiss; three show, and "+ N more" opens the rest in place. Each group's
 * Dismiss acts on that group alone, and a reminder's on that reminder. From 1 December, while next year's statutory
 * holidays aren't imported, a last group says so and opens Settings › Schedule. With none of these, there is no box.
 * @param {object} props
 * @param {object} props.day - The day on show, today.
 * @param {object|null} props.yesterday - Yesterday's tasks to fix, from the local service.
 * @param {object[]} props.reminders - Today's reminders, as the local service gives them (see reminderLine).
 * @param {object[]} props.rows - Today's tasks, to open the one a reminder names.
 * @param {boolean} props.backendConnected - Whether Ava can change anything.
 * @param {(text: string, send: boolean) => void} props.onAskAva - Open Ava with a request.
 * @param {(date: string) => void} props.onDismissYesterday - Hide yesterday's group.
 * @param {(ids: string[]) => void} props.onDismissReminders - Dismiss reminders, by their ids.
 * @param {(row: object) => void} props.onOpenRow - Open a task's panel.
 * @param {() => void} props.onPlans - Compare today's plans.
 * @param {(area: string) => void} props.onSeeTasks - Show an area's tasks.
 * @param {(goal: {domain: string, goalId: string}) => void} props.onAddStep - Add a task to a goal.
 */
function TodayNotices({ day, yesterday, reminders, rows, backendConnected, onAskAva, onDismissYesterday, onDismissReminders,
  onOpenRow, onPlans, onSeeTasks, onAddStep }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <div className="dw-banner dw-banner-history dw-banner-titled dw-today-notices">
      {yesterday && <YesterdayNotice notice={yesterday} backendConnected={backendConnected} onAskAva={onAskAva}
        onDismiss={onDismissYesterday} />}
      {yesterday && reminders.length > 0 && <hr className="dw-notices-divider" />}
      {reminders.length > 0 && (
        <section className="dw-notice-group dw-reminders" aria-labelledby="dw-reminders-title">
          <Icon name="agent" size={18} />
          <div className="dw-banner-text">
            <h2 id="dw-reminders-title" className="dw-label">{t("remindersTitle", { count: reminders.length })}</h2>
            <ul className="dw-reminder-list">
              {(open ? reminders : reminders.slice(0, REMINDERS_SHOWN)).map((item) => {
                const line = reminderLine(item, day.date, t);
                return line && (
                  <li key={item.id} className="dw-reminder">
                    {DOMAINS.includes(item.agentKey) && <AreaTag domain={item.agentKey} />}
                    <span className="dw-reminder-text">{line.text}</span>
                    <span className="dw-reminder-since">{line.since}</span>
                    <span className="dw-reminder-actions">
                      <ReminderAction item={item} action={line.action} rows={rows} backendConnected={backendConnected}
                        onAskAva={onAskAva} onOpenRow={onOpenRow} onPlans={onPlans} onSeeTasks={onSeeTasks} onAddStep={onAddStep} />
                      <button type="button" className="dw-button dw-button-quiet" aria-label={t("reminderDismissNamed", { reminder: line.text })}
                        onClick={() => onDismissReminders([item.id])}>{t("dismissAction")}</button>
                    </span>
                  </li>
                );
              })}
            </ul>
            {!open && reminders.length > REMINDERS_SHOWN && (
              <button type="button" className="dw-button dw-button-quiet dw-reminders-more" onClick={() => setOpen(true)}>
                {t("remindersMore", { count: reminders.length - REMINDERS_SHOWN })}</button>
            )}
          </div>
          <div className="dw-actions">
            <button type="button" className="dw-button dw-button-quiet" aria-label={t("remindersDismissAll")}
              onClick={() => onDismissReminders(reminders.map((shown) => shown.id))}>{t("dismissAction")}</button>
          </div>
        </section>
      )}
      {(yesterday || reminders.length > 0) && day.holidayReminder && <hr className="dw-notices-divider" />}
      {day.holidayReminder && (
        <section className="dw-notice-group dw-holiday-reminder" aria-labelledby="dw-holiday-reminder-title">
          <Icon name="calendar" size={18} />
          <div className="dw-banner-text">
            <h2 id="dw-holiday-reminder-title" className="dw-label">{t("holidayReminderTitle", { year: day.holidayReminder })}</h2>
            <p>{t("holidayReminderText")}</p>
          </div>
          <div className="dw-actions">
            <button type="button" className="dw-button" onClick={() => openSettings("schedule")}>{t("holidayReminderAction")}</button>
          </div>
        </section>
      )}
    </div>
  );
}

/**
 * The one thing to do about a reminder (see REMINDER_ACTIONS): plan a session with Ava, typed for the user to send, or,
 * while she can't answer, the line saying she needs a model; add the goal's next step; see the area's tasks; compare
 * today's plans; or change the task's length in its panel, or with the task not on today, see its area's tasks.
 * @param {object} props
 * @param {object} props.item - The reminder, as the local service gives it.
 * @param {string} props.action - What can be done about it, from REMINDER_ACTIONS.
 * @param {object[]} props.rows - Today's tasks, to open the one it names.
 * @param {boolean} props.backendConnected - Whether Ava can change anything.
 * @param {(text: string, send: boolean) => void} props.onAskAva - Open Ava with a request.
 * @param {(row: object) => void} props.onOpenRow - Open a task's panel.
 * @param {() => void} props.onPlans - Compare today's plans.
 * @param {(area: string) => void} props.onSeeTasks - Show an area's tasks.
 * @param {(goal: {domain: string, goalId: string}) => void} props.onAddStep - Add a task to a goal.
 */
function ReminderAction({ item, action, rows, backendConnected, onAskAva, onOpenRow, onPlans, onSeeTasks, onAddStep }) {
  const { t } = useI18n();
  if (!action) return null;
  const label = t(REMINDER_ACTIONS[action]);
  if (action === "planSession") {
    return (
      <AvaOnly>
        <button type="button" className="dw-button" disabled={!backendConnected}
          onClick={() => onAskAva(t("reminderPlanPrompt", { title: item.values.goalTitle }), false)}>{label}</button>
      </AvaOnly>
    );
  }
  const row = rows.find((candidate) => candidate.title === item.values.taskTitle);
  const act = {
    addStep: () => onAddStep({ domain: item.agentKey, goalId: item.values.goalId }),
    seeTasks: () => onSeeTasks(item.agentKey),
    comparePlans: () => onPlans(),
    changeLength: () => (row ? onOpenRow(row) : onSeeTasks(item.agentKey)),
  }[action];
  return <button type="button" className="dw-button" onClick={act}>{label}</button>;
}

/**
 * Today's energy, out of 5, if the user wants to say it: each tap adds a reading, any time today,
 * and the day's average of them is what counts. One line, "Energy" and the scale; the latest reading
 * shows only as its selected button. A low average has plans put Lighter day first, which the Life
 * agent's notes explain, and a high one Deep focus.
 * @param {object} props
 * @param {number|null} props.level - Today's latest reading, or null before one is given.
 * @param {boolean} props.backendConnected - Whether a reading can be saved.
 * @param {(level: number) => void} props.onEnergy - Report a reading.
 */
function EnergyRow({ level, backendConnected, onEnergy }) {
  const { t } = useI18n();
  return (
    <fieldset className="dw-energy-row" disabled={!backendConnected}>
      <legend className="dw-visually-hidden">{t("energyQuestion")}</legend>
      <span className="dw-label" aria-hidden="true">{t("energyLabel")}</span>
      <Segmented label={t("energyQuestion")} value={level ? String(level) : ""} onChange={(value) => onEnergy(Number(value))}
        options={ENERGY_LEVELS.map((value) => [value, value])} />
    </fieldset>
  );
}

/**
 * The day's schedule: one row per task or plan entry, with a line marking the current time.
 * @param {object} props
 * @param {object[]} props.rows - Rows sorted by start time.
 * @param {object[]} props.meals - The set plan's lunch and dinner, shown in place as breaks.
 * @param {object|null} props.next - The next action, marked on its row.
 * @param {number} props.now - Minutes after midnight now.
 * @param {boolean} props.backendConnected - Whether a report can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {(row: object) => void} props.onOpen - Show a row's details.
 */
function Schedule({ rows, meals, next, now, backendConnected, onStatus, onOpen }) {
  const { t, language } = useI18n();
  /**
   * Where a row sits in the day, at the time it shows: when it started, once its status kept the time it took, else
   * when it is planned to.
   */
  const shownAt = (row) => minutesOf(timeTaken(row)?.start || row.start_time);
  const shown = [...rows, ...meals].sort((first, second) => shownAt(first) - shownAt(second));
  const nowIndex = shown.findIndex((row) => shownAt(row) > now);
  const plannedMinutes = totalMinutes(rows);
  const allEntries = rows.every((row) => row.kind === "entry");
  return (
    <section className="dw-card" aria-labelledby="dw-schedule-title">
      <div className="dw-card-head">
        <h2 id="dw-schedule-title" className="dw-heading">{t("scheduleTitle")}</h2>
        <span className="dw-caption">{rows.length} {allEntries ? t("entriesCount") : t("tasksCount")} · {formatMinutes(plannedMinutes, language)} {t("plannedSuffix")}</span>
      </div>
      <ol className="dw-schedule">
        {shown.map((row, index) => (
          <li key={row.id}>
            {index === nowIndex && <NowLine now={now} />}
            {row.kind === "meal"
              ? <div className="dw-meal-row"><TimeColumn row={row} />
                <span className="dw-meal-label"><Icon name="meal" size={16} />{t(`mealName${row.title}`)}</span></div>
              : <ScheduleRow row={row} isNext={next?.id === row.id} now={now} backendConnected={backendConnected} onStatus={onStatus} onOpen={onOpen} />}
          </li>
        ))}
        {nowIndex === -1 && shown.length > 0 && <li><NowLine now={now} /></li>}
      </ol>
    </section>
  );
}

/**
 * The day's flexible tasks that have no start time yet. They sit under the schedule until a plan
 * the user sets gives them one, and they can be reported here meanwhile.
 * @param {object} props
 * @param {object[]} props.rows - Rows without a start time.
 * @param {object|null} props.next - The next action, marked on its row when it is one of these.
 * @param {boolean} props.backendConnected - Whether a report can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {(row: object) => void} props.onOpen - Show a row's details.
 */
function UntimedTasks({ rows, next, backendConnected, onStatus, onOpen }) {
  const { t, language } = useI18n();
  const minutes = totalMinutes(rows);
  return (
    <section className="dw-card dw-untimed" aria-labelledby="dw-untimed-title">
      <div className="dw-card-head">
        <h2 id="dw-untimed-title" className="dw-heading">{t("untimed")}</h2>
        <span className="dw-caption">{rows.length} {t("tasksCount")} · {formatMinutes(minutes, language)}</span>
      </div>
      <p className="dw-caption">{t("untimedNote")}</p>
      <ol className="dw-schedule">
        {rows.map((row) => (
          <li key={row.id}>
            <ScheduleRow row={row} isNext={next?.id === row.id} now={0} backendConnected={backendConnected} onStatus={onStatus} onOpen={onOpen} />
          </li>
        ))}
      </ol>
    </section>
  );
}

/**
 * A thin rule at the current time, between the entries before and after it.
 * @param {object} props
 * @param {number} props.now - The time, in minutes after midnight.
 */
function NowLine({ now }) {
  const { t } = useI18n();
  return <div className="dw-now" role="presentation"><span>{t("nowLabel")} {clockOf(now)}</span></div>;
}

/**
 * One task or plan entry: its time, area, title, flags and a single status control. A task without
 * a start time shows only its length in the time column.
 * @param {object} props
 * @param {object} props.row - The row to show.
 * @param {boolean} props.isNext - Whether it is the next action.
 * @param {number} props.now - Minutes after midnight now.
 * @param {boolean} props.backendConnected - Whether a report can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report its status.
 * @param {(row: object) => void} props.onOpen - Show its details.
 */
function ScheduleRow({ row, isNext, now, backendConnected, onStatus, onOpen }) {
  const { t, serviceText } = useI18n();
  const ended = Boolean(row.start_time) && minutesOf(row.start_time) + row.duration_minutes <= now;
  const unreported = ended && row.completion_status === "planned";
  const source = row.source;
  const fixed = row.constraint_kind === "fixed";
  const repeats = source?.repeatKind && source.repeatKind !== "none";
  // A task is paused with its goal; only resuming the goal makes it reportable again.
  const paused = isPaused(row);
  // A task that ran to its limit, twice its length, without a status stopped there; it waits for one.
  const limited = Boolean((source || row).limitStopped) && row.completion_status === "planned";
  return (
    <div className={`dw-row dw-row-${row.completion_status}${paused ? " dw-row-paused" : ""}`}>
      <TimeColumn row={row} />
      <div className={`dw-row-block dw-area-${areaOf(row.domain)}`}>
        <button type="button" className="dw-row-body" aria-label={`${row.title}, ${row.start_time || t("untimed")}. ${t("openDetails")}`} onClick={() => onOpen(row)}>
          <span className="dw-row-title"><AreaTag domain={row.domain} /><span>{row.title}</span>{isNext && <span className="dw-chip dw-chip-ink dw-chip-small">{t("nextLabel")}</span>}
            <span className="dw-row-flags">
              {fixed && <span><Icon name="pin" size={16} />{t("flagFixed")}</span>}
              {repeats && <span><Icon name="repeat" size={16} />{t(source.repeatKind === "daily" ? "flagDaily" : "flagWeekly")}</span>}
            </span></span>
          {row.detail && <span className="dw-row-detail">{serviceText(row.detail)}</span>}
          {row.outsidePlan && <span className="dw-row-note"><Icon name="info" size={16} />{t("notInSetPlan")}</span>}
          {limited && !paused && <span className="dw-row-note"><Icon name="alert" size={16} />{t("limitStoppedNote")}</span>}
          {unreported && !paused && !limited && <span className="dw-row-note"><Icon name="clock" size={16} />{t("notReportedYet")}</span>}
          {paused && <span className="dw-row-note dw-row-paused-note"><Icon name="pause" size={16} />{t("taskGoalPaused")}</span>}
        </button>
        <StatusControl value={row.completion_status} noReply={noReplyOf(row)} title={row.title} disabled={!backendConnected} paused={paused}
          onChange={(status) => onStatus(row, status)} />
      </div>
    </div>
  );
}

/**
 * The next thing to do, with the status reported right here. A task without a start time shows
 * its length instead of a time range.
 * @param {object} props
 * @param {object} props.row - The next row.
 * @param {number} props.now - Minutes after midnight now.
 * @param {object[]} props.goals - The user's goals, to name a linked one.
 * @param {boolean} props.backendConnected - Whether a report can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report its status.
 */
function NextCard({ row, now, goals, backendConnected, onStatus }) {
  const { t, language } = useI18n();
  const startsIn = row.start_time ? minutesOf(row.start_time) - now : 0;
  const when = !row.start_time ? t("untimed")
    : startsIn > 0 ? `${t("inPrefix")} ${formatMinutes(startsIn, language)}` : t("nowLabel");
  const goal = goals.find((candidate) => candidate.id === row.source?.goalId);
  return (
    <section className={`dw-card dw-next dw-area-${areaOf(row.domain)}`} aria-labelledby="dw-next-title">
      <div className="dw-card-head">
        <span className="dw-chip dw-chip-ink">{t("nextLabel")} · {when}</span>
        <AreaTag domain={row.domain} />
      </div>
      <p className="dw-next-time">{row.start_time ? timeRange(row.start_time, row.duration_minutes) : taskLength(row, language)}</p>
      <h2 id="dw-next-title" className="dw-next-title">{row.title}</h2>
      {goal && <p className="dw-row-flags"><span><Icon name="link" size={16} />{goal.title}</span></p>}
      <p className="dw-label">{t("reportWhatHappened")}</p>
      <StatusControl variant="segmented" value={row.completion_status} noReply={noReplyOf(row)} title={row.title} disabled={!backendConnected}
        onChange={(status) => onStatus(row, status)} />
    </section>
  );
}

/**
 * Planned time by area, with the time spent filled in: the time each reported task took, whatever its
 * status (see spentMinutes). Nothing counts until it is reported.
 * @param {object} props
 * @param {object[]} props.rows - The day's rows.
 */
function BalanceCard({ rows }) {
  const { t, language } = useI18n();
  const byArea = DOMAINS.map((domain) => {
    const inArea = rows.filter((row) => row.domain === domain);
    return {
      domain,
      planned: totalMinutes(inArea),
      reported: totalMinutes(inArea, spentMinutes),
    };
  });
  const total = totalMinutes(byArea, (area) => area.planned);
  return (
    <section className="dw-card" aria-labelledby="dw-balance-title">
      <div className="dw-card-head"><h2 id="dw-balance-title" className="dw-heading">{t("balanceTitle")}</h2><span className="dw-caption">{t("plannedReported")}</span></div>
      <div className="dw-stack" aria-hidden="true">
        {total > 0 && byArea.filter((area) => area.planned).map((area) => (
          <span key={area.domain} className={`dw-area-${areaOf(area.domain)}`} style={{ flexGrow: area.planned }} />
        ))}
      </div>
      <ul className="dw-balance">
        {byArea.map((area) => (
          <li key={area.domain}>
            <AreaTag domain={area.domain} plain />
            <span className={`dw-track dw-area-${areaOf(area.domain)}`}>
              {area.planned > 0 && <span style={{ width: `${Math.round((area.reported / area.planned) * 100)}%` }} />}
            </span>
            <span className="dw-caption">{formatMinutes(area.reported, language)} / {formatMinutes(area.planned, language)}</span>
          </li>
        ))}
      </ul>
      <p className="dw-caption">{total ? t("balanceFootnote") : t("balanceEmpty")}</p>
    </section>
  );
}

/**
 * The first-run desk: what to add, in order, and what DayWright will never do on its own.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => void} props.onGoals - Add a goal.
 * @param {() => void} props.onAddTask - Add a task.
 */
function EmptyToday({ backendConnected, onGoals, onAddTask }) {
  const { t } = useI18n();
  return (
    <section className="dw-card dw-empty" aria-labelledby="dw-empty-title">
      <h2 id="dw-empty-title" className="dw-title">{t("nothingPlannedYet")}</h2>
      <p className="dw-body-lg">{t("nothingPlannedHelp")}</p>
      <ol className="dw-steps">
        <li><h3>{t("stepGoal")}</h3><p>{t("stepGoalHelp")}</p>
          <button type="button" className="dw-button" disabled={!backendConnected} onClick={onGoals}><Icon name="plus" size={18} />{t("newGoalAction")}</button></li>
        <li><h3>{t("stepTasks")}</h3><p>{t("stepTasksHelp")}</p>
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addTaskAction")}</button></li>
        <li><h3>{t("stepPropose")}</h3><p>{t("stepProposeHelp")}</p>
          <button type="button" className="dw-button" disabled aria-describedby="dw-propose-reason"><Icon name="agent" size={18} />{t("proposePlansAction")}</button>
          <p id="dw-propose-reason" className="dw-caption">{t("proposeNeedsTask")}</p></li>
      </ol>
      <ul className="dw-reassure">
        <li><Icon name="laptop" size={18} /><strong>{t("savedOnMac")}</strong><span>{t("savedOnMacHelp")}</span></li>
        <li><Icon name="pencil" size={18} /><strong>{t("nothingInvented")}</strong><span>{t("nothingInventedHelp")}</span></li>
        <li><Icon name="check" size={18} /><strong>{t("nothingSetWithoutYou")}</strong><span>{t("nothingSetWithoutYouHelp")}</span></li>
      </ul>
    </section>
  );
}
