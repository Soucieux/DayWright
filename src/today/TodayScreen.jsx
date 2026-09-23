import { useI18n } from "../i18n";
import { AreaTag, areaOf } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { StatusControl } from "../ui/StatusControl";
import { clockOf, clockOfTimestamp, formatMinutes, longDate, minutesOf, nowMinutes, timeRange } from "../time";
import { planName } from "../plans/planName";
import { SuggestionCard } from "../records/SuggestionCard";
import { dayRows } from "./dayRows";

/** Areas in the order Balance lists them. */
const BALANCE_AREAS = ["learning", "life", "finance", "rest"];

/** Advice priority order: strong advice is shown before soft. */
const PRIORITY_ORDER = { strong: 0, soft: 1 };

/**
 * The workbench for today: one schedule, the next action, and the few facts that describe the day.
 * @param {object} props
 * @param {object} props.day - Today's records, plan and model state.
 * @param {object|null} props.pool - Saved Summary advice by period.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {(row: object) => void} props.onOpenRow - Show a row's details, with Edit and Remove.
 * @param {() => void} props.onPropose - Ask the agents for alternatives.
 * @param {() => void} props.onPlans - Open the plan comparison.
 * @param {() => void} props.onGoals - Open goals in Records.
 * @param {() => void} props.onAddTask - Record a new task.
 * @param {() => void} props.onReplace - Ask for a replacement of the set plan.
 * @param {(adviceId: string) => void} props.onDismissAdvice - Stop an idea being dispatched.
 * @param {(item: object, decision: "accept"|"dismiss") => Promise<void>} props.onDecide - Add or dismiss an agent's suggestion.
 */
export function TodayScreen({ day, pool, backendConnected, onStatus, onOpenRow, onPropose, onPlans, onGoals, onAddTask, onReplace, onDismissAdvice, onDecide }) {
  const { t, language, demoText } = useI18n();
  const { weekday, dayMonth } = longDate(day.date, language);
  const { rows, fromPlan, suggestions } = dayRows(day);
  const drafts = !fromPlan && day.planSetId ? day.variants.length : 0;
  const empty = !rows.length && !day.planSetId;
  const now = nowMinutes();
  const remaining = rows.filter((row) => row.completion_status === "planned" || row.completion_status === "partial");
  const next = remaining.find((row) => minutesOf(row.start_time) + row.duration_minutes > now) || null;
  const reported = rows.filter((row) => row.completion_status !== "planned");
  const reportedMinutes = rows.filter((row) => ["done", "partial"].includes(row.completion_status))
    .reduce((total, row) => total + row.duration_minutes, 0);
  const plannedMinutes = rows.reduce((total, row) => total + row.duration_minutes, 0);
  const setVariant = day.variants.find((variant) => variant.id === day.confirmedVariantId);
  const setAt = clockOfTimestamp(day.confirmedAt);

  return (
    <main className="dw-page" tabIndex={-1}>
      <header className="dw-page-head">
        <div>
          <p className="dw-eyebrow">{weekday}</p>
          <h1 className="dw-display">{dayMonth}</h1>
          <div className="dw-chips">
            {fromPlan && <span className="dw-chip dw-chip-ink"><Icon name="check" size={14} />{t("planSetChip")} · {planName(setVariant, t, demoText)}{setAt && ` · ${setAt}`}</span>}
            {drafts > 0 && <span className="dw-chip dw-chip-dashed"><Icon name="pencil" size={14} />{drafts} {t("draftsNotSet")}</span>}
            {rows.length > 0 && <span className="dw-chip"><Icon name="check" size={14} />{t("reportedChip")} {reported.length} / {rows.length} · {formatMinutes(reportedMinutes, language)} / {formatMinutes(plannedMinutes, language)}</span>}
            {fromPlan && day.variants.length > 1 && <button type="button" className="dw-chip dw-chip-link" onClick={onPlans}><Icon name="eye" size={14} />{day.variants.length} {t("plansProposedView")}</button>}
            {empty && <span className="dw-chip"><Icon name="info" size={14} />{t("nothingRecordedToday")}</span>}
          </div>
        </div>
        {!empty && (
          <div className="dw-page-actions">
            <button type="button" className="dw-button" disabled={!backendConnected} onClick={onAddTask}><Icon name="plus" size={18} />{t("addTaskAction")}</button>
            {fromPlan
              ? <button type="button" className="dw-button" disabled={!backendConnected} onClick={onReplace}><Icon name="history" size={18} />{t("askReplacement")}</button>
              : drafts > 0
                ? <button type="button" className="dw-button dw-button-primary" onClick={onPlans}>{t("compareAndSet")}</button>
                : <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} onClick={onPropose}><Icon name="agent" size={18} />{t("proposePlansAction")}</button>}
          </div>
        )}
      </header>

      <PageBanners day={day} backendConnected={backendConnected} />

      <div className="dw-columns">
        <div className="dw-column-main">
          {suggestions.map((item) => <SuggestionCard key={item.id} item={item} backendConnected={backendConnected} onDecide={onDecide} />)}
          {empty
            ? <EmptyToday backendConnected={backendConnected} onGoals={onGoals} onAddTask={onAddTask} />
            : <Schedule rows={rows} next={next} now={now} backendConnected={backendConnected} onStatus={onStatus} onOpen={onOpenRow} />}
        </div>
        <aside className="dw-column-side" aria-label={t("aboutTheDay")}>
          {next && <NextCard row={next} now={now} goals={day.goals} backendConnected={backendConnected} onStatus={onStatus} />}
          <AdviceCard pool={pool} backendConnected={backendConnected} onDismiss={onDismissAdvice} />
          <BalanceCard rows={rows} />
          <GoalsCard goals={day.goals} onGoals={onGoals} />
        </aside>
      </div>
    </main>
  );
}

/**
 * The day's schedule: one row per task or plan entry, with a line marking the current time.
 * @param {object} props
 * @param {object[]} props.rows - Rows sorted by start time.
 * @param {object|null} props.next - The next action, marked on its row.
 * @param {number} props.now - Minutes after midnight now.
 * @param {boolean} props.backendConnected - Whether a report can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report a row's status.
 * @param {(row: object) => void} props.onOpen - Show a row's details.
 */
function Schedule({ rows, next, now, backendConnected, onStatus, onOpen }) {
  const { t, language } = useI18n();
  const nowIndex = rows.findIndex((row) => minutesOf(row.start_time) > now);
  const plannedMinutes = rows.reduce((total, row) => total + row.duration_minutes, 0);
  const allEntries = rows.every((row) => row.kind === "entry");
  return (
    <section className="dw-card" aria-labelledby="dw-schedule-title">
      <div className="dw-card-head">
        <h2 id="dw-schedule-title" className="dw-heading">{t("scheduleTitle")}</h2>
        <span className="dw-caption">{rows.length} {allEntries ? t("entriesCount") : t("tasksCount")} · {formatMinutes(plannedMinutes, language)} {t("plannedSuffix")}</span>
      </div>
      <ol className="dw-schedule">
        {rows.map((row, index) => (
          <li key={row.id}>
            {index === nowIndex && <NowLine now={now} />}
            <ScheduleRow row={row} isNext={next?.id === row.id} now={now} backendConnected={backendConnected} onStatus={onStatus} onOpen={onOpen} />
          </li>
        ))}
        {nowIndex === -1 && rows.length > 0 && <li><NowLine now={now} /></li>}
      </ol>
    </section>
  );
}

/** A thin rule at the current time, between the entries before and after it. */
function NowLine({ now }) {
  const { t } = useI18n();
  return <div className="dw-now" role="presentation"><span>{t("nowLabel")} {clockOf(now)}</span></div>;
}

/**
 * One task or plan entry: its time, area, title, flags and a single status control.
 * @param {object} props
 * @param {object} props.row - The row to show.
 * @param {boolean} props.isNext - Whether it is the next action.
 * @param {number} props.now - Minutes after midnight now.
 * @param {boolean} props.backendConnected - Whether a report can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report its status.
 * @param {(row: object) => void} props.onOpen - Show its details.
 */
function ScheduleRow({ row, isNext, now, backendConnected, onStatus, onOpen }) {
  const { t, language, demoText } = useI18n();
  const ended = minutesOf(row.start_time) + row.duration_minutes <= now;
  const unreported = ended && row.completion_status === "planned";
  const source = row.source;
  const fixed = row.constraint_kind === "fixed";
  const repeats = source?.repeatKind && source.repeatKind !== "none";
  return (
    <div className={`dw-row dw-row-${row.completion_status}`}>
      <div className="dw-row-time">
        <span className="dw-row-start">{row.start_time}</span>
        <span className="dw-caption">{formatMinutes(row.duration_minutes, language)}</span>
      </div>
      <div className="dw-row-block">
        <button type="button" className="dw-row-body" aria-label={`${demoText(row.title)}, ${row.start_time}. ${t("openDetails")}`} onClick={() => onOpen(row)}>
          <span className="dw-row-title"><AreaTag domain={row.domain} /><span>{demoText(row.title)}</span>{isNext && <span className="dw-chip dw-chip-ink dw-chip-small">{t("nextLabel")}</span>}</span>
          {row.detail && <span className="dw-row-detail">{demoText(row.detail)}</span>}
          {row.outsidePlan && <span className="dw-row-note"><Icon name="info" size={16} />{t("notInSetPlan")}</span>}
          {unreported && <span className="dw-row-note"><Icon name="clock" size={16} />{t("notReportedYet")}</span>}
          <span className="dw-row-flags">
            {fixed && <span><Icon name="pin" size={16} />{t("flagFixed")}</span>}
            {Boolean(source?.protected) && <span><Icon name="shield" size={16} />{t("flagProtected")}</span>}
            {repeats && <span><Icon name="repeat" size={16} />{t(source.repeatKind === "daily" ? "flagDaily" : "flagWeekly")}</span>}
          </span>
        </button>
        <StatusControl value={row.completion_status} title={demoText(row.title)} disabled={!backendConnected}
          onChange={(status) => onStatus(row, status)} />
      </div>
    </div>
  );
}

/**
 * The next thing to do, with the status reported right here.
 * @param {object} props
 * @param {object} props.row - The next row.
 * @param {number} props.now - Minutes after midnight now.
 * @param {object[]} props.goals - The user's goals, to name a linked one.
 * @param {boolean} props.backendConnected - Whether a report can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report its status.
 */
function NextCard({ row, now, goals, backendConnected, onStatus }) {
  const { t, language, demoText } = useI18n();
  const startsIn = minutesOf(row.start_time) - now;
  const goal = goals.find((candidate) => candidate.id === row.source?.goalId);
  return (
    <section className="dw-card dw-next" aria-labelledby="dw-next-title">
      <div className="dw-card-head">
        <span className="dw-chip dw-chip-ink">{startsIn > 0 ? `${t("nextLabel")} · ${t("inPrefix")} ${formatMinutes(startsIn, language)}` : `${t("nextLabel")} · ${t("nowLabel")}`}</span>
        <AreaTag domain={row.domain} />
      </div>
      <p className="dw-next-time">{timeRange(row.start_time, row.duration_minutes)}</p>
      <h2 id="dw-next-title" className="dw-next-title">{demoText(row.title)}</h2>
      {goal && <p className="dw-row-flags"><span><Icon name="link" size={16} />{demoText(goal.title)}</span></p>}
      <p className="dw-label">{t("reportWhatHappened")}</p>
      <StatusControl variant="segmented" value={row.completion_status} title={demoText(row.title)} disabled={!backendConnected}
        onChange={(status) => onStatus(row, status)} />
    </section>
  );
}

/**
 * Today's Summary advice, pencilled because an agent wrote it. Advice stays active until the user
 * dismisses it; there is no separate "keep" to record.
 * @param {object} props
 * @param {object|null} props.pool - Saved advice by period.
 * @param {boolean} props.backendConnected - Whether a dismissal can be saved.
 * @param {(adviceId: string) => void} props.onDismiss - Stop the idea being dispatched.
 */
function AdviceCard({ pool, backendConnected, onDismiss }) {
  const { t, demoText } = useI18n();
  const advice = [...(pool?.day?.items || [])]
    .filter((item) => item.status === "active")
    .sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 2) - (PRIORITY_ORDER[b.priority] ?? 2))[0];
  return (
    <section className="dw-card dw-pencilled" aria-labelledby="dw-advice-title">
      <p className="dw-agent-line"><span className="dw-agent-mark"><Icon name="agent" size={16} /></span>
        <strong id="dw-advice-title">{t("summaryAgent")}</strong><span className="dw-caption">· {t("adviceLabel")}</span></p>
      {advice ? (
        <>
          <p className="dw-advice-text">{demoText(advice.content)}</p>
          <p className="dw-evidence"><Icon name="info" size={16} /><span>{t("adviceEvidence")} · <AreaTag domain={advice.domain} plain /> · {t(advice.priority)}</span></p>
          <div className="dw-actions">
            <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => onDismiss(advice.id)}>{t("dismissAction")}</button>
            <span className="dw-caption">{t("adviceStaysActive")}</span>
          </div>
        </>
      ) : <p className="dw-muted">{t("noAdviceYet")}</p>}
    </section>
  );
}

/**
 * Planned time by area, with the reported part filled in. Nothing counts until it is reported.
 * @param {object} props
 * @param {object[]} props.rows - The day's rows.
 */
function BalanceCard({ rows }) {
  const { t, language } = useI18n();
  const byArea = BALANCE_AREAS.map((domain) => {
    const inArea = rows.filter((row) => row.domain === domain);
    return {
      domain,
      planned: inArea.reduce((total, row) => total + row.duration_minutes, 0),
      reported: inArea.filter((row) => ["done", "partial"].includes(row.completion_status)).reduce((total, row) => total + row.duration_minutes, 0),
    };
  });
  const total = byArea.reduce((sum, area) => sum + area.planned, 0);
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
 * Active goals and how far the reported work has taken each.
 * @param {object} props
 * @param {object[]} props.goals - The user's goals.
 * @param {() => void} props.onGoals - Open all goals.
 */
function GoalsCard({ goals, onGoals }) {
  const { t, demoText } = useI18n();
  const active = goals.filter((goal) => goal.status === "active");
  return (
    <section className="dw-card" aria-labelledby="dw-goals-title">
      <div className="dw-card-head"><h2 id="dw-goals-title" className="dw-heading">{t("goalsTitle")}</h2>
        {goals.length > 0 && <button type="button" className="dw-link" onClick={onGoals}>{t("allGoals")}<Icon name="right" size={16} /></button>}</div>
      {active.length ? (
        <ul className="dw-goal-list">
          {active.slice(0, 3).map((goal) => (
            <li key={goal.id}>
              <p className="dw-goal-name"><AreaTag domain={goal.domain} plain /><span>{demoText(goal.title)}</span></p>
              <span className={`dw-track dw-area-${areaOf(goal.domain)}`}>
                {goal.itemCount > 0 && <span style={{ width: `${Math.round((goal.doneCount / goal.itemCount) * 100)}%` }} />}
              </span>
              <span className="dw-caption">{goal.doneCount} / {goal.itemCount} {t("linkedTasksReported")}</span>
            </li>
          ))}
        </ul>
      ) : <><p>{t("noGoalsYet")}</p><p className="dw-caption">{t("goalsOptional")}</p></>}
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
