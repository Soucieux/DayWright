import { useI18n } from "../i18n";
import { addDays } from "../calendar/month";
import { noticeText } from "../talk/notices";
import { formatMinutes, nowMinutes, shortDate } from "../time";
import { DayStrip } from "../today/DayStrip";
import { dayRows } from "../today/dayRows";
import { DAY_END_MINUTES, DAY_START_MINUTES } from "../today/stripLayout";
import { AreaGlyph, areaOf } from "../ui/AreaTag";
import { DayDots, HabitWeek, LoadBars, PracticeDots, StepBar } from "../ui/AreaVisuals";
import { Icon } from "../ui/Icon";
import { StatusControl } from "../ui/StatusControl";
import { TimeColumn } from "../ui/TimeColumn";
import { agentName } from "../ui/agentName";
import {
  CARD_TEXT, EMPTY_STATES, askMoveText, barTime, byDay, carryStatusText, dayRange, habitRule, habitStopped, noteIcon,
  projectStatusText, streakText,
} from "./areaOverview";

/** The days of a list that runs over a week of days, from its first. */
const SPAN_DAYS = 7;
/** The reports that count a task as done. */
const DONE = new Set(["done", "partial"]);
/** The chip each project status wears. */
const PROJECT_CHIPS = { "on-track": "dw-chip-saved", stalled: "dw-chip-caution", paused: "dw-chip-history", "no-steps": "" };

/**
 * The seven days from one day on.
 * @param {string} first - The first YYYY-MM-DD day.
 * @returns {string[]} It and the six days after it.
 */
const daysFrom = (first) => Array.from({ length: SPAN_DAYS }, (_, offset) => addDays(first, offset));

/**
 * One card of an area's screen: its title with the days it covers, the line saying what it counts, then its content.
 * @param {object} props
 * @param {string} props.id - Names the card, for its heading's id.
 * @param {string} props.title - The card's title.
 * @param {string} props.window - The days it covers, as dayRange or shortDate words them.
 * @param {string} props.counts - What it counts, in one line.
 * @param {boolean} [props.pencilled=false] - Drawn dashed, as what an agent says is.
 * @param {import("react").ReactNode} props.children - Its numbers, visual and rows.
 */
function AreaCard({ id, title, window, counts, pencilled = false, children }) {
  return (
    <section className={`dw-card dw-area-card${pencilled ? " dw-pencilled" : ""}`} aria-labelledby={`dw-card-${id}`}>
      <header className="dw-area-card-head">
        <h2 id={`dw-card-${id}`} className="dw-heading">{title} <span className="dw-area-card-window">· {window}</span></h2>
        <p className="dw-caption">{counts}</p>
      </header>
      {children}
    </section>
  );
}

/**
 * A card's empty state: what fills it, and the action that does.
 * @param {object} props
 * @param {string} props.kind - The card, as EMPTY_STATES names it.
 * @param {object} [props.values] - Values for its words, such as the area.
 * @param {string} [props.detail] - A further line under the words.
 * @param {() => void} props.onAction - Take the action.
 * @param {string} [props.icon="plus"] - The action's icon.
 * @param {boolean} [props.disabled=false] - The action can't be taken now.
 */
function Empty({ kind, values, detail, onAction, icon = "plus", disabled = false }) {
  const { t } = useI18n();
  const { text, action } = EMPTY_STATES[kind];
  return (
    <div className="dw-area-empty">
      <p className="dw-muted">{t(text, values)}</p>
      {detail && <p className="dw-caption">{detail}</p>}
      <button type="button" className="dw-button dw-button-quiet" disabled={disabled} onClick={onAction}>
        <Icon name={icon} size={18} />{t(action, values)}</button>
    </div>
  );
}

/**
 * A task on any day, opening its details: its time, area, title, a line under it, and its status.
 * @param {object} props
 * @param {object} props.item - The task, with `start_time`, `duration_minutes` and `completion_status`.
 * @param {string} props.domain - Its area.
 * @param {string} [props.caption] - The line under its title.
 * @param {(item: object) => void} props.onOpen - Show its details.
 */
function DayItemRow({ item, domain, caption, onOpen }) {
  const { t, demoText } = useI18n();
  return (
    <button type="button" className="dw-day-row" onClick={() => onOpen(item)}
      aria-label={`${demoText(item.title)}, ${item.start_time || t("noStartTime")}, ${t(item.completion_status)}. ${t("openDetails")}`}>
      <TimeColumn row={item} />
      <AreaGlyph domain={domain} />
      <span className="dw-day-row-title">{demoText(item.title)}{caption && <span className="dw-caption">{caption}</span>}</span>
      <StatusControl readOnly value={item.completion_status} />
    </button>
  );
}

/**
 * A list over days: a dot per day, then each day with its tasks.
 * @param {object} props
 * @param {string[]} props.dates - The seven days the list covers.
 * @param {object[]} props.items - Its tasks, each with its `date`.
 * @param {string} props.domain - Their area.
 * @param {string} props.label - The dot row's accessible name.
 * @param {boolean} [props.newestFirst=false] - List the latest day first.
 * @param {(item: object) => string} [props.caption] - The line under a task's title.
 * @param {(item: object) => void} props.onOpen - Show a task's details.
 */
function DayList({ dates, items, domain, label, newestFirst = false, caption, onOpen }) {
  const { language } = useI18n();
  const groups = byDay(items);
  return (
    <>
      <DayDots dates={dates} items={items} label={label} area={areaOf(domain)} />
      <div className="dw-area-days">
        {(newestFirst ? [...groups].reverse() : groups).map((group) => (
          <section key={group.date} aria-label={shortDate(group.date, language)}>
            <h3 className="dw-section-label">{shortDate(group.date, language)}</h3>
            <ul className="dw-day-rows">
              {group.items.map((item) => (
                <li key={item.id}><DayItemRow item={item} domain={domain} caption={caption?.(item)} onOpen={onOpen} /></li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  );
}

/**
 * Today in an area, or the day on show: the area's strip and its tasks with their times and statuses,
 * Add task on today and later days, and See all for the area's Tasks.
 * @param {object} props
 * @param {string} props.domain - The area.
 * @param {object} props.day - The day on show.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {(defaults: object) => void} props.onAddTask - Record a task in the area.
 * @param {() => void} props.onSeeAll - Show the area's tasks in Tasks.
 */
export function TodayCard({ domain, day, today, backendConnected, onOpenRow, onStatus, onAddTask, onSeeAll }) {
  const { t, language, demoText } = useI18n();
  const area = t(domain);
  const past = day.date < today;
  const isToday = day.date === today;
  const { timed, rows } = dayRows(day);
  const mine = rows.filter((row) => row.domain === domain);
  const title = isToday ? t(CARD_TEXT.today.title, { area }) : t("areaDayTitle", { date: shortDate(day.date, language), area });
  const minutes = mine.reduce((sum, row) => sum + (row.duration_minutes || 0), 0);
  return (
    <AreaCard id="today" title={title} window={shortDate(day.date, language)} counts={t(CARD_TEXT.today.counts, { area })}>
      <DayStrip timed={timed} now={isToday ? nowMinutes() : past ? DAY_END_MINUTES : DAY_START_MINUTES} dayMeals={day.meals || []}
        area={domain} showNow={isToday} label={title} />
      {mine.length ? (
        <>
          <p className="dw-area-stats">{t("areaDayStats", { count: mine.length, done: mine.filter((row) => DONE.has(row.completion_status)).length,
            minutes: formatMinutes(minutes, language) })}</p>
          <ul className="dw-area-tasks">
            {mine.map((row) => (
              <li key={`${row.kind}-${row.id}`}>
                <TimeColumn row={row} />
                <AreaGlyph domain={row.domain} />
                {past ? <span className="dw-area-task-title">{demoText(row.title)}</span> : (
                  <button type="button" className="dw-area-task-title" onClick={() => onOpenRow(row)}
                    aria-label={`${demoText(row.title)}, ${row.start_time || t("noStartTime")}. ${t("openDetails")}`}>{demoText(row.title)}</button>
                )}
                <StatusControl value={row.completion_status} title={demoText(row.title)} readOnly={past} disabled={!backendConnected}
                  paused={row.source?.goalStatus === "paused"} onChange={(status) => onStatus(row, status)} />
              </li>
            ))}
          </ul>
        </>
      ) : past ? <Empty kind="todayPast" values={{ area }} icon="search" onAction={onSeeAll} />
        : <Empty kind="today" values={{ area }} disabled={!backendConnected} onAction={() => onAddTask({ domain })} />}
      <div className="dw-actions dw-area-card-actions">
        {mine.length > 0 && !past && (
          <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => onAddTask({ domain })}>
            <Icon name="plus" size={18} />{t("addTaskAction")}</button>
        )}
        {!(past && !mine.length) && <button type="button" className="dw-link" onClick={onSeeAll}>{t("areaSeeAll", { area })}</button>}
      </div>
    </AreaCard>
  );
}

/**
 * The area agent's notes on today: its findings and flags, each with an icon for its kind, or that
 * nothing needs flagging; on another day, that its notes are for today.
 * @param {object} props
 * @param {string} props.domain - The area.
 * @param {object[]|null} props.notes - Today's notes, as the local service gives them; null on another day.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {() => void} props.onToday - Show today.
 * @param {() => void} props.onAskAva - Open Ava.
 */
export function NotesCard({ domain, notes, today, onToday, onAskAva }) {
  const { t, language, demoText } = useI18n();
  const agent = agentName(domain, t);
  return (
    <AreaCard id="notes" pencilled title={t(CARD_TEXT.notes.title, { agent })} window={shortDate(today, language)}
      counts={t(CARD_TEXT.notes.counts, { agent })}>
      {notes === null ? (
        <div className="dw-area-empty">
          <p className="dw-muted">{t("notesForToday")}</p>
          <button type="button" className="dw-button dw-button-quiet" onClick={onToday}><Icon name="calendar" size={18} />{t("showTodayAction")}</button>
        </div>
      ) : notes.length ? (
        <ul className="dw-area-notes">
          {notes.map((note, index) => (
            <li key={`${note.kind}-${index}`}>
              <span className="dw-agent-mark"><Icon name={noteIcon(note.kind)} size={16} /></span>
              <span>{noticeText(note, t, language, demoText)}</span>
            </li>
          ))}
        </ul>
      ) : <Empty kind="notes" detail={t("notesHow", { agent })} icon="talk" onAction={onAskAva} />}
    </AreaCard>
  );
}

/**
 * Learning's subjects: each Learning goal's time done against planned this week, its practice row,
 * when it was last practised and its next session; then the time on Learning tasks without a goal.
 * @param {object} props
 * @param {object} props.data - Learning's overview.
 * @param {boolean} props.canAdd - Whether a task or goal can be added now.
 * @param {(goalId: string) => void} props.onEditGoal - Open a goal's Edit sheet.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {(defaults: object) => void} props.onAddTask - Record a task.
 * @param {(domain: string) => void} props.onNewGoal - Start a goal in the area.
 * @param {() => void} props.onSeeAll - Show Learning's tasks in Tasks.
 */
export function SubjectsCard({ data, canAdd, onEditGoal, onOpenTask, onAddTask, onNewGoal, onSeeAll }) {
  const { t, language, demoText } = useI18n();
  const minutes = (value) => formatMinutes(value, language);
  const dates = daysFrom(data.weekStart);
  const area = t("learning");
  return (
    <AreaCard id="subjects" title={t(CARD_TEXT.subjects.title)} window={dayRange(data.weekStart, data.weekEnd, language)}
      counts={t(CARD_TEXT.subjects.counts)}>
      {data.subjects.length || data.other.plannedMinutes ? (
        <ul className="dw-area-items">
          {data.subjects.map((subject) => (
            <li key={subject.goalId}>
              <div className="dw-area-item-head">
                <button type="button" className="dw-area-item-title" onClick={() => onEditGoal(subject.goalId)}>{demoText(subject.title)}</button>
                {subject.status === "paused" && <span className="dw-chip dw-chip-small dw-chip-history">{t("pausedLabel")}</span>}
                <span className="dw-area-figure">{t("subjectTime", { done: minutes(subject.doneMinutes), planned: minutes(subject.plannedMinutes) })}</span>
              </div>
              <span className={`dw-track dw-area-${areaOf("learning")}`} aria-hidden="true">
                <span style={{ width: `${subject.plannedMinutes ? Math.round((subject.doneMinutes / subject.plannedMinutes) * 100) : 0}%` }} />
              </span>
              <PracticeDots days={subject.days} dates={dates} label={`${demoText(subject.title)}: ${t("practiceTitle")}`} />
              <p className="dw-caption">{subject.lastPractised ? t("lastPractisedOn", { date: shortDate(subject.lastPractised, language) }) : t("notPractisedYet")}</p>
              {subject.nextSession ? (
                <button type="button" className="dw-link dw-area-next" onClick={() => onOpenTask(subject.nextSession)}>
                  {t("nextSessionLabel", { title: demoText(subject.nextSession.title),
                    when: [shortDate(subject.nextSession.date, language), subject.nextSession.start_time].filter(Boolean).join(" ") })}</button>
              ) : subject.status === "active" && (
                <button type="button" className="dw-button dw-button-quiet dw-icon-only" disabled={!canAdd}
                  aria-label={t("addSessionLabel", { goal: demoText(subject.title) })} title={t("addSessionLabel", { goal: demoText(subject.title) })}
                  onClick={() => onAddTask({ domain: "learning", goalId: subject.goalId })}><Icon name="plus" size={18} /></button>
              )}
            </li>
          ))}
          <li>
            <div className="dw-area-item-head">
              <span className="dw-area-item-title">{t("notInAGoal")}</span>
              <span className="dw-area-figure">{t("subjectTime", { done: minutes(data.other.doneMinutes), planned: minutes(data.other.plannedMinutes) })}</span>
            </div>
            <button type="button" className="dw-link" onClick={onSeeAll}>{t("areaSeeAll", { area })}</button>
          </li>
        </ul>
      ) : <Empty kind="subjects" values={{ area }} disabled={!canAdd} onAction={() => onNewGoal("learning")} />}
    </AreaCard>
  );
}

/**
 * Learning's practice this week: a bar per day of the time planned, the part done darker, with the week's totals.
 * @param {object} props
 * @param {object} props.data - Learning's overview.
 * @param {boolean} props.canAdd - Whether a task can be added now.
 * @param {(defaults: object) => void} props.onAddTask - Record a task.
 */
export function PracticeCard({ data, canAdd, onAddTask }) {
  const { t, language } = useI18n();
  const planned = data.practice.reduce((sum, day) => sum + day.plannedMinutes, 0);
  const done = data.practice.reduce((sum, day) => sum + day.doneMinutes, 0);
  return (
    <AreaCard id="practice" title={t(CARD_TEXT.practice.title)} window={dayRange(data.weekStart, data.weekEnd, language)}
      counts={t(CARD_TEXT.practice.counts)}>
      {planned ? (
        <>
          <LoadBars days={data.practice.map((day) => ({ date: day.date, value: day.plannedMinutes, done: day.doneMinutes }))}
            area={areaOf("learning")} label={t(CARD_TEXT.practice.title)} current={data.date} valueText={(bar) => barTime(bar.value)}
            dayLabel={(bar) => t("barPlannedDone", { day: shortDate(bar.date, language), done: formatMinutes(bar.done, language),
              planned: formatMinutes(bar.value, language) })} />
          <p className="dw-area-stats">{t("weekTotals", { done: formatMinutes(done, language), planned: formatMinutes(planned, language) })}</p>
        </>
      ) : <Empty kind="practice" disabled={!canAdd} onAction={() => onAddTask({ domain: "learning" })} />}
    </AreaCard>
  );
}

/**
 * Life's habits: each repeat's rule and start, its week grid, its count and its streak; one stopped
 * this week stays listed, marked with the day it stopped.
 * @param {object} props
 * @param {object} props.data - Life's overview.
 * @param {boolean} props.canAdd - Whether a task can be added now.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {(defaults: object) => void} props.onAddTask - Record a task.
 */
export function HabitsCard({ data, canAdd, onOpenTask, onAddTask }) {
  const { t, language, demoText } = useI18n();
  const dates = daysFrom(data.weekStart);
  return (
    <AreaCard id="habits" title={t(CARD_TEXT.habits.title)} window={dayRange(data.weekStart, data.weekEnd, language)}
      counts={t(CARD_TEXT.habits.counts)}>
      {data.habits.length ? (
        <ul className="dw-area-items">
          {data.habits.map((habit) => {
            const stopped = habitStopped(habit, t, language);
            return (
              <li key={habit.seriesId}>
                <div className="dw-area-item-head">
                  <button type="button" className="dw-area-item-title" onClick={() => onOpenTask({ id: habit.itemId, date: habit.itemDate })}>
                    {demoText(habit.title)}</button>
                  <span className="dw-chip dw-chip-small"><Icon name="repeat" size={14} />{habitRule(habit, t, language)}</span>
                  {stopped && <span className="dw-chip dw-chip-small dw-chip-caution">{stopped}</span>}
                </div>
                <HabitWeek days={habit.days} dates={dates} label={`${demoText(habit.title)}: ${t(CARD_TEXT.habits.title)}`} />
                <p className="dw-caption">{t("doneThisWeek", { count: habit.doneThisWeek })} · {streakText(habit, t)}</p>
              </li>
            );
          })}
        </ul>
      ) : <Empty kind="habits" disabled={!canAdd} onAction={() => onAddTask({ domain: "life" })} />}
    </AreaCard>
  );
}

/**
 * The day's shape: the whole day's strip with its key, Life's appointments and the meals with their
 * times, and the free windows between 09:00 and 22:00.
 * @param {object} props
 * @param {object} props.data - Life's overview.
 * @param {object} props.day - The day on show.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 */
export function ShapeCard({ data, day, today, onOpenTask }) {
  const { t, language } = useI18n();
  const title = t(day.date === today ? CARD_TEXT.shape.title : "shapeDayTitle");
  const meals = data.meals.map((meal) => ({ ...meal, id: `meal-${meal.title}`, meal: true }));
  const rows = [...data.appointments, ...meals].sort((a, b) => a.start_time.localeCompare(b.start_time));
  return (
    <AreaCard id="shape" title={title} window={shortDate(day.date, language)} counts={t(CARD_TEXT.shape.counts)}>
      <DayStrip timed={dayRows(day).timed} now={DAY_START_MINUTES} dayMeals={day.meals || []} whole showNow={false} label={title} />
      <ul className="dw-day-rows">
        {rows.map((row) => (
          <li key={row.id}>
            {row.meal ? (
              <div className="dw-day-row">
                <TimeColumn row={row} /><Icon name="meal" size={14} /><span className="dw-day-row-title">{t(`mealName${row.title}`)}</span><span />
              </div>
            ) : <DayItemRow item={{ ...row, date: day.date }} domain="life" onOpen={onOpenTask} />}
          </li>
        ))}
      </ul>
      <h3 className="dw-section-label">{t("freeWindowsLabel")}</h3>
      {data.freeWindows.length ? (
        <ul className="dw-area-windows">
          {data.freeWindows.map((window) => (
            <li key={window.start}><span>{window.start}–{window.end}</span><span className="dw-caption">{formatMinutes(window.minutes, language)}</span></li>
          ))}
        </ul>
      ) : <p className="dw-muted">{t("noFreeWindows")}</p>}
    </AreaCard>
  );
}

/**
 * Life's energy over the seven days to the day on show: a bar per reading, 1 to 5, a guide at 2,
 * and low readings in the caution colour.
 * @param {object} props
 * @param {object} props.data - Life's overview.
 * @param {() => void} props.onTodayScreen - Go to Today, where energy is reported.
 */
export function EnergyCard({ data, onTodayScreen }) {
  const { t, language } = useI18n();
  const week = data.energyWeek;
  return (
    <AreaCard id="energy" title={t(CARD_TEXT.energy.title)} window={dayRange(week[0].date, week[week.length - 1].date, language)}
      counts={t(CARD_TEXT.energy.counts)}>
      {week.some((day) => day.level) ? (
        <>
          <LoadBars days={week.map((day) => ({ date: day.date, value: day.level, done: day.level || 0 }))} area={areaOf("life")} label={t(CARD_TEXT.energy.title)}
            scale={{ max: 5, guide: 2, low: 2 }} current={data.date} valueText={(bar) => bar.value ?? t("energyNoReading")}
            dayLabel={(bar) => t("barReading", { day: shortDate(bar.date, language),
              level: bar.value ? t("energyOf", { level: bar.value }) : t("notReportedShort") })} />
          <p className="dw-caption dw-energy-guide-note"><span className="dw-energy-guide-swatch" aria-hidden="true" />{t("energyGuide")}</p>
        </>
      ) : <Empty kind="energy" icon="sun" onAction={onTodayScreen} />}
    </AreaCard>
  );
}

/**
 * Work's load this week: a bar per day of the time planned, the part done darker, with the week's totals.
 * @param {object} props
 * @param {object} props.data - Work's overview.
 * @param {boolean} props.canAdd - Whether a task can be added now.
 * @param {(defaults: object) => void} props.onAddTask - Record a task.
 */
export function LoadCard({ data, canAdd, onAddTask }) {
  const { t, language } = useI18n();
  return (
    <AreaCard id="load" title={t(CARD_TEXT.load.title)} window={dayRange(data.weekStart, data.weekEnd, language)} counts={t(CARD_TEXT.load.counts)}>
      {data.plannedMinutes ? (
        <>
          <LoadBars days={data.load.map((day) => ({ date: day.date, value: day.minutes, done: day.doneMinutes }))}
            area={areaOf("work")} label={t(CARD_TEXT.load.title)} current={data.date} valueText={(bar) => barTime(bar.value)}
            dayLabel={(bar) => t("barPlannedDone", { day: shortDate(bar.date, language), done: formatMinutes(bar.done, language),
              planned: formatMinutes(bar.value, language) })} />
          <p className="dw-area-stats">{t("weekTotals", { done: formatMinutes(data.doneMinutes, language),
            planned: formatMinutes(data.plannedMinutes, language) })}</p>
        </>
      ) : <Empty kind="load" disabled={!canAdd} onAction={() => onAddTask({ domain: "work" })} />}
    </AreaCard>
  );
}

/**
 * Work's meetings: its tasks with a start time from the day on show through the next six, by day.
 * @param {object} props
 * @param {object} props.data - Work's overview.
 * @param {boolean} props.canAdd - Whether a task can be added now.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {(defaults: object) => void} props.onAddTask - Record a task.
 */
export function MeetingsCard({ data, canAdd, onOpenTask, onAddTask }) {
  const { t, language } = useI18n();
  const dates = daysFrom(data.date);
  return (
    <AreaCard id="meetings" title={t(CARD_TEXT.meetings.title)} window={dayRange(dates[0], dates[SPAN_DAYS - 1], language)}
      counts={t(CARD_TEXT.meetings.counts)}>
      {data.meetings.length ? <DayList dates={dates} items={data.meetings} domain="work" label={t(CARD_TEXT.meetings.title)} onOpen={onOpenTask} />
        : <Empty kind="meetings" disabled={!canAdd} onAction={() => onAddTask({ domain: "work" })} />}
    </AreaCard>
  );
}

/**
 * Work carried over: its tasks of the seven days before that are not reported, partly done or moved
 * on, each with its day and status; one not moved offers Ask Ava to move.
 * @param {object} props
 * @param {object} props.data - Work's overview.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {(text: string) => void} props.onAskAva - Open Ava with a request typed in, not sent.
 * @param {() => void} props.onSeeAll - Show Work's tasks in Tasks.
 */
export function CarryOversCard({ data, onOpenTask, onAskAva, onSeeAll }) {
  const { t, language, demoText } = useI18n();
  const items = data.carryOvers;
  const count = (test) => items.filter(test).length;
  return (
    <AreaCard id="carry" title={t(CARD_TEXT.carryOvers.title)} window={dayRange(addDays(data.date, -SPAN_DAYS), addDays(data.date, -1), language)}
      counts={t(CARD_TEXT.carryOvers.counts)}>
      {items.length ? (
        <>
          <p className="dw-area-stats">{t("carryCounts", { open: count((item) => !item.movedTo && item.status === "planned"),
            partial: count((item) => !item.movedTo && item.status === "partial"), moved: count((item) => item.movedTo) })}</p>
          <ul className="dw-area-carry">
            {items.map((item) => (
              <li key={`${item.date}-${item.title}`}>
                <button type="button" className="dw-area-item-title" disabled={!item.id}
                  onClick={() => onOpenTask({ id: item.id, date: item.movedTo || item.date })}>
                  {demoText(item.title)}<span className="dw-caption">{shortDate(item.date, language)}</span></button>
                <span className={`dw-chip dw-chip-small${item.movedTo ? " dw-chip-history" : item.status === "planned" ? " dw-chip-caution" : ""}`}>
                  {carryStatusText(item, t, language)}</span>
                {!item.movedTo && (
                  <button type="button" className="dw-button dw-button-quiet" onClick={() => onAskAva(askMoveText(item, t, language))}>
                    <Icon name="talk" size={16} />{t("askAvaToMove")}</button>
                )}
              </li>
            ))}
          </ul>
        </>
      ) : <Empty kind="carryOvers" values={{ area: t("work") }} icon="search" onAction={onSeeAll} />}
    </AreaCard>
  );
}

/**
 * Project's projects: each Project goal's status in plain words, its step bar and steps done, its
 * last step and its next one, or Add the next step.
 * @param {object} props
 * @param {object} props.data - Project's overview.
 * @param {boolean} props.canAdd - Whether a task or goal can be added now.
 * @param {(goalId: string) => void} props.onEditGoal - Open a goal's Edit sheet.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {(defaults: object) => void} props.onAddTask - Record a task.
 * @param {(domain: string) => void} props.onNewGoal - Start a goal in the area.
 */
export function ProjectsCard({ data, canAdd, onEditGoal, onOpenTask, onAddTask, onNewGoal }) {
  const { t, language, demoText } = useI18n();
  const step = (key, item) => t(key, { title: demoText(item.title), date: shortDate(item.date, language) });
  return (
    <AreaCard id="projects" title={t(CARD_TEXT.projects.title)} window={shortDate(data.date, language)} counts={t(CARD_TEXT.projects.counts)}>
      {data.projects.length ? (
        <ul className="dw-area-items">
          {data.projects.map((project) => {
            const done = t("stepsDone", { done: project.done, total: project.total });
            return (
              <li key={project.goalId}>
                <div className="dw-area-item-head">
                  <button type="button" className="dw-area-item-title" onClick={() => onEditGoal(project.goalId)}>{demoText(project.title)}</button>
                  <span className={`dw-chip dw-chip-small ${PROJECT_CHIPS[project.health]}`.trim()}>{projectStatusText(project, t)}</span>
                </div>
                {project.total > 0 && (
                  <>
                    <StepBar steps={project.steps} label={`${demoText(project.title)}: ${done}`} />
                    <p className="dw-caption">{done}</p>
                  </>
                )}
                <p className="dw-caption">{project.lastStep ? step("lastStepLabel", project.lastStep) : t("noStepYet")}</p>
                {project.nextStep ? (
                  <button type="button" className="dw-link dw-area-next" onClick={() => onOpenTask(project.nextStep)}>{step("nextStepLabel", project.nextStep)}</button>
                ) : project.status === "active" && (
                  <button type="button" className="dw-button dw-button-quiet" disabled={!canAdd}
                    onClick={() => onAddTask({ domain: "project", goalId: project.goalId })}><Icon name="plus" size={18} />{t("addNextStep")}</button>
                )}
              </li>
            );
          })}
        </ul>
      ) : <Empty kind="projects" values={{ area: t("project") }} disabled={!canAdd} onAction={() => onNewGoal("project")} />}
    </AreaCard>
  );
}

/**
 * Project's next steps: its tasks still to do from the day on show through the next six, by day, with their project.
 * @param {object} props
 * @param {object} props.data - Project's overview.
 * @param {boolean} props.canAdd - Whether a task can be added now.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {(defaults: object) => void} props.onAddTask - Record a task.
 */
export function NextStepsCard({ data, canAdd, onOpenTask, onAddTask }) {
  const { t, language, demoText } = useI18n();
  const dates = daysFrom(data.date);
  return (
    <AreaCard id="next" title={t(CARD_TEXT.nextSteps.title)} window={dayRange(dates[0], dates[SPAN_DAYS - 1], language)}
      counts={t(CARD_TEXT.nextSteps.counts)}>
      {data.nextSteps.length ? (
        <DayList dates={dates} items={data.nextSteps} domain="project" label={t(CARD_TEXT.nextSteps.title)} onOpen={onOpenTask}
          caption={(item) => (item.goalTitle ? demoText(item.goalTitle) : t("noProjectGoal"))} />
      ) : <Empty kind="nextSteps" disabled={!canAdd} onAction={() => onAddTask({ domain: "project" })} />}
    </AreaCard>
  );
}

/**
 * Project's recently done: its tasks done or partly done in the seven days to the day on show, newest first, with their project.
 * @param {object} props
 * @param {object} props.data - Project's overview.
 * @param {(item: object) => void} props.onOpenTask - Show a task's details.
 * @param {() => void} props.onSeeAll - Show Project's tasks in Tasks.
 */
export function RecentlyDoneCard({ data, onOpenTask, onSeeAll }) {
  const { t, language, demoText } = useI18n();
  const dates = daysFrom(addDays(data.date, 1 - SPAN_DAYS));
  return (
    <AreaCard id="recent" title={t(CARD_TEXT.recentDone.title)} window={dayRange(dates[0], dates[SPAN_DAYS - 1], language)}
      counts={t(CARD_TEXT.recentDone.counts)}>
      {data.recentDone.length ? (
        <DayList dates={dates} items={data.recentDone} domain="project" label={t(CARD_TEXT.recentDone.title)} newestFirst onOpen={onOpenTask}
          caption={(item) => (item.goalTitle ? demoText(item.goalTitle) : t("noProjectGoal"))} />
      ) : <Empty kind="recentDone" values={{ area: t("project") }} icon="search" onAction={onSeeAll} />}
    </AreaCard>
  );
}
