import { useEffect, useRef, useState } from "react";
import { Check, ChevronLeft, ChevronRight, MessageSquare, Mic, Pin, Send, Sparkles, Target, X } from "lucide-react";
import { api, getDay } from "./api";
import { DomainRecordsBoard } from "./DomainRecords";
import { useWorkspace } from "./workspace";
import { BottomBar, PhoneHeader, RecordsNav, TopBar } from "./shell/Shell";
import { beginVoiceCapture } from "./voice";
import { LanguageProvider, useI18n } from "./i18n";

const domainMeta = {
  learning: { label: "Learn", color: "#f1512e", statement: "steady progress" },
  life: { label: "Life", color: "#245fe5", statement: "moderate pace" },
  finance: { label: "Finance", color: "#24855f", statement: "on track" },
  rest: { label: "Rest", color: "#66615c", statement: "protected" },
};

const modeCopy = {
  ask: ["Ask", "Understand the plan or weigh a tradeoff."],
  adjust: ["Adjust", "Describe a change. DayWright will propose it for confirmation."],
  report: ["Report", "Talk through what happened; completion remains explicit."],
};

function formatDuration(minutes) {
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}h ${String(remainder).padStart(2, "0")}m` : `${hours}h 00m`;
}

function timeRange(start, durationMinutes) {
  const [hour, minute] = start.split(":").map(Number);
  const endMinutes = (hour * 60 + minute + durationMinutes) % (24 * 60);
  return `${start}–${String(Math.floor(endMinutes / 60)).padStart(2, "0")}:${String(endMinutes % 60).padStart(2, "0")}`;
}

function dateParts(value, language = "en") {
  const date = new Date(`${value}T12:00:00`);
  const locale = language === "zh" ? "zh-CN" : "en";
  return {
    day: new Intl.DateTimeFormat(locale, { weekday: "short" }).format(date).toUpperCase(),
    dayNumber: new Intl.DateTimeFormat(locale, { day: "2-digit" }).format(date),
    monthYear: new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(date),
  };
}

function monthTitle(month, language = "en") {
  return new Intl.DateTimeFormat(language === "zh" ? "zh-CN" : "en", { month: "long", year: "numeric" }).format(new Date(`${month}-01T12:00:00`));
}

function shiftMonth(month, offset) {
  const value = new Date(`${month}-01T12:00:00`);
  value.setMonth(value.getMonth() + offset);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

function calendarDates(month) {
  const first = new Date(`${month}-01T12:00:00`);
  const offset = (first.getDay() + 6) % 7;
  first.setDate(first.getDate() - offset);
  return Array.from({ length: 42 }, (_, index) => {
    const value = new Date(first);
    value.setDate(first.getDate() + index);
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  });
}

function Icon({ name }) {
  const icons = { chat: MessageSquare, spark: Sparkles, mic: Mic, send: Send, close: X, pin: Pin, check: Check };
  const Component = icons[name];
  return <Component aria-hidden="true" />;
}

function Notice({ message }) {
  if (!message) return null;
  return <div className="notice" role="status">{message}</div>;
}

function AgentTrail({ route }) {
  const { t, demoText } = useI18n();
  if (!route?.length) return null;
  return (
    <div className="agent-trail" aria-label={route.map((run) => t(run.agentKey)).join(", ")}>
      <small>{t("agentRoute")}</small>
      <div>
        {route.map((run, index) => (
          <span className={`agent-chip agent-${run.agentKey}`} key={`${run.agentKey}-${run.phase}-${index}`} title={demoText(run.summary)}>
            <b>{String(index + 1).padStart(2, "0")}</b>{t(run.agentKey)}<i>{t(run.phase)}</i>
          </span>
        ))}
      </div>
    </div>
  );
}

function RetrievalTrail({ retrieval }) {
  const { t, demoText } = useI18n();
  if (!retrieval?.matches?.length) return null;
  const sources = Array.from(
    new Map(retrieval.matches.map((match) => [match.sourceId, match])).values(),
  );
  return (
    <div className="retrieval-trail" aria-label={`Retrieved sources: ${sources.map((source) => source.sourceTitle).join(", ")}`}>
      <small>{t("retrievedSources")} / SQLITE-VEC</small>
      <div>
        {sources.map((source) => (
          <span key={source.sourceId} title={demoText(source.content)}>
            <b>{source.sourceType}</b>{source.sourceUrl ? <a href={source.sourceUrl} target="_blank" rel="noopener noreferrer">{demoText(source.sourceTitle)} ↗</a> : demoText(source.sourceTitle)}<i>{t("chunk")} {source.chunkIndex + 1}{source.sourceLicense && ` · ${source.sourceLicense}`}</i>
          </span>
        ))}
      </div>
    </div>
  );
}

function StatusControl({ entry, onUpdate }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const labels = { planned: t("report"), done: t("done"), partial: t("partial"), skipped: t("skipped") };
  return (
    <div className="status-control">
      <button
        className={`status-trigger status-${entry.completion_status}`}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={`${t("progressFor")} ${entry.title}`}
      >
        {entry.completion_status === "done" && <Icon name="check" />}
        {labels[entry.completion_status]}
      </button>
      {open && (
        <div className="status-menu">
          {["done", "partial", "skipped", "planned"].map((status) => (
            <button key={status} onClick={() => { onUpdate(entry.id, status); setOpen(false); }}>
              {labels[status]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Schedule({ entries, onUpdate, canReport = false, title, showTimeRange = false }) {
  const { t, demoText } = useI18n();
  return (
    <section className={`schedule ${showTimeRange ? "time-range" : ""}`} aria-labelledby="schedule-title">
      <div className="schedule-heading">
        <span>{t("time")}</span><span id="schedule-title">{title || t("daySchedule")}</span><span>{t("area")}</span>
      </div>
      {entries.map((entry) => {
        const meta = domainMeta[entry.domain];
        const isBuffer = entry.title.toLowerCase().includes("buffer");
        return (
          <article
            className={`schedule-row domain-${entry.domain} ${isBuffer ? "buffer" : ""} completion-${entry.completion_status}`}
            key={entry.id}
          >
            <time>{showTimeRange ? timeRange(entry.start_time, entry.duration_minutes) : entry.start_time}</time>
            <div className="task-copy">
              <span className="domain-rule" />
              <h3>{demoText(entry.title)}</h3>
              <p>{demoText(entry.detail)}</p>
              {entry.constraint_kind === "fixed" && <strong className="constraint"><Icon name="pin" /> {t("fixed")}</strong>}
              {isBuffer && <strong className="constraint flexible">{t("flexible")}</strong>}
              {canReport && <StatusControl entry={entry} onUpdate={onUpdate} />}
            </div>
            <div className="area-copy">
              <b style={{ color: meta.color }}>{t(entry.domain).toUpperCase()}</b>
              {!showTimeRange && <span>{formatDuration(entry.duration_minutes)}</span>}
            </div>
          </article>
        );
      })}
    </section>
  );
}

function DaySummary({ day }) {
  const { t, demoText } = useI18n();
  const entries = day.planSetId ? day.entries : day.dayItems || [];
  const managed = day.dayItems || [];
  const done = entries.filter((entry) => entry.completion_status === "done").length;
  const partial = entries.filter((entry) => entry.completion_status === "partial").length;
  const skipped = entries.filter((entry) => entry.completion_status === "skipped").length;
  const planName = day.variants?.find((variant) => variant.id === day.confirmedVariantId)?.name;
  return (
    <section className="day-summary" aria-label={`${t("daySchedule")} ${day.date}`}>
      <div className="section-line"><small>{t("daySchedule")} / {day.date}</small><b>{day.confirmedVariantId ? `${t("confirmed")} · ${demoText(planName)}` : day.planSetId ? `${t("draft")} · ${t("notConfirmed")}` : managed.length ? t("recordedDay") : t("noTimedItems")}</b></div>
      <div className="summary-totals">
        <div><strong>{entries.length}</strong><span>{t("scheduled")}</span></div>
        <div><strong>{done}</strong><span>{t("done")}</span></div>
        <div><strong>{partial}</strong><span>{t("partial")}</span></div>
        <div><strong>{skipped}</strong><span>{t("skipped")}</span></div>
      </div>
      <div className="domain-totals">
        {Object.entries(domainMeta).map(([domain, meta]) => (
          <span key={domain} style={{ borderColor: meta.color }}><b>{t(domain)}</b>{formatDuration(day.planSetId ? day.balance?.[domain] || 0 : managed.filter((item) => item.domain === domain).reduce((total, item) => total + item.duration_minutes, 0))}</span>
        ))}
      </div>
      {day.planSetId && managed.length > 0 && <p className="managed-summary">{t("managedRecord")}: {managed.filter((item) => item.completion_status === "done").length}/{managed.length} {t("done")}. {t("savedSnapshot")}</p>}
    </section>
  );
}

/** Make Summary-agent day, week, and month reports visible with their evidence. */
function SummaryPanel({ reports, pool = null, date, onOpen, compact = false, embedded = false }) {
  const { t, demoText } = useI18n();
  const [kind, setKind] = useState("day");
  const report = reports?.[kind];
  const periodAdvice = (pool?.[kind]?.items || []).filter((item) => item.status === "active");
  const broaderAdvice = Object.values(pool || {}).flatMap((period) => period.items || []).filter((item) => item.status === "active");
  const pooledAdvice = periodAdvice.length ? periodAdvice : broaderAdvice;
  const nextSuggestions = Array.from(new Map([...(report?.suggestions || []), ...pooledAdvice]
    .map((item) => [`${item.domain}:${item.content}`, item])).values())
    .sort((left, right) => Number(right.priority === "strong") - Number(left.priority === "strong"));
  const domainRows = report ? Object.entries(report.domains || {}).filter(([, counts]) => counts.scheduled > 0) : [];
  const scheduled = domainRows.reduce((total, [, counts]) => total + counts.scheduled, 0);
  const done = domainRows.reduce((total, [, counts]) => total + counts.done, 0);
  const completion = scheduled ? Math.round((done / scheduled) * 100) : 0;
  return <section className={`summary-panel ${compact ? "compact" : ""} ${embedded ? "embedded" : ""}`} aria-label={`${t("summaryAgent")} ${date}`}>
    <div className="summary-heading"><div><small>{t("summaryAgent")}</small><h2>{t("recordsSay")}</h2></div><div className="summary-switch" aria-label={t("summaryAgent")}>{["day", "week", "month"].map((period) => <button key={period} className={kind === period ? "active" : ""} onClick={() => setKind(period)} aria-pressed={kind === period}>{t(period)}</button>)}</div></div>
    {report ? <>
      <div className="summary-scoreboard"><span><strong>{report.recordedDays}</strong><small>{t("recordedDays")}</small></span><span><strong>{completion}%</strong><small>{t("completed")}</small></span><span><strong>{nextSuggestions.length}</strong><small>{t("nextIdeas")}</small></span></div>
      <div className="summary-body"><div className="summary-patterns"><small>{t("byArea")} · {report.periodKey}</small>{domainRows.length ? domainRows.map(([domain, counts]) => <div key={domain}><b style={{ color: domainMeta[domain]?.color }}>{t(domain)}</b><span>{counts.done}/{counts.scheduled} {t("done")}{counts.partial ? ` · ${counts.partial} ${t("partial")}` : ""}{counts.skipped ? ` · ${counts.skipped} ${t("skipped")}` : ""}</span></div>) : <p>{t("noReportedWork")}</p>}</div><div className="summary-next"><small>{t("nextBestStep")}</small>{nextSuggestions.length ? nextSuggestions.slice(0, 2).map((suggestion, index) => <p key={`${suggestion.domain}-${index}`}><b>{suggestion.domain === "cross" ? t("acrossAreas") : t(suggestion.domain)}</b>{demoText(suggestion.content)}</p>) : <p>{t("keepRecording")}</p>}</div></div>
      {report.feedback.length > 0 && <details className="summary-memory"><summary>{t("preferenceMemory")} ({report.feedback.length})</summary>{report.feedback.map((signal) => <p key={`${signal.domain}-${signal.taskTitle}`}>{signal.shortenRequests} · {demoText(signal.taskTitle)}</p>)}</details>}
      <div className="summary-footer"><small>{t("basedOnSaved")} ({report.knowledgeSourceCount})</small>{onOpen && <button onClick={onOpen}>{t("openHistory")}</button>}</div>
    </> : <p className="empty-copy">{reports ? t("noReport") : t("startServiceSummary")}</p>}
  </section>;
}

function SuggestionPoolPanel({ pool, onDiscard, onClearWeek }) {
  const { t, demoText } = useI18n();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState("day");
  const [domain, setDomain] = useState("all");
  const current = pool?.[kind];
  const items = (current?.items || []).filter((item) => domain === "all" || item.domain === domain);
  const notices = (current?.notices || []).filter((item) => domain === "all" || item.domain === domain);
  const activeCount = new Set(Object.values(pool || {}).flatMap((period) =>
    period.items.filter((item) => item.status === "active")
      .map((item) => `${item.domain}:${item.content}`))).size;
  return <section className="suggestion-pool" aria-label={t("savedAdvice")}>
    <div className="section-line"><small>{t("savedAdvice")} / {activeCount}</small>
      <button onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        {open ? t("closeAdvice") : t("manageAdvice")}</button></div>
    {open && <>
      <div className="pool-filters" aria-label="Suggestion filters">
        {(["day", "week", "month"]).map((value) => <button key={value} onClick={() => setKind(value)}
          aria-pressed={kind === value}>{value.toUpperCase()}</button>)}
        <select aria-label="Suggestion area" value={domain} onChange={(event) => setDomain(event.target.value)}>
          <option value="all">{t("allAreas")}</option>{["learning", "life", "finance", "rest", "cross"].map((value) =>
            <option key={value} value={value}>{t(value)}</option>)}</select>
      </div>
      <small className="pool-period">{current?.periodKey || t("noLocalReport")}</small>
      {items.length ? items.map((item) => <div className="pool-item" key={item.id}>
        <span><b>{t(item.domain)} · {t(item.priority).toUpperCase()} · {t(item.status).toUpperCase()}</b><p>{demoText(item.content)}</p></span>
        {item.status === "active" && <button onClick={() => onDiscard(item.id)}>{t("discardAdvice")}</button>}
      </div>) : <p className="empty-copy">{t("noAdvice")}</p>}
      {notices.map((item, index) => <p className="pool-notice" key={`${item.domain}-${index}`} role="status">
        {t("discardedAgain")}: {demoText(item.content)}</p>)}
      {kind === "week" && domain !== "all" && (items.length > 0 || notices.length > 0) &&
        <button className="pool-clear" onClick={() => onClearWeek(current.periodKey, domain)}>
          {t("clearWeekArea")}</button>}
      <p className="empty-copy">{t("adviceHelp")}</p>
    </>}
  </section>;
}

/** Collect or edit one dated task without silently turning it into a plan. */
function DayItemForm({ date, goals, item, defaultDomain = "life", defaultGoalId = "", onSave, backendConnected, onCancel }) {
  const { t } = useI18n();
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setDraft(item ? {
    date: item.date, title: item.title, detail: item.detail, domain: item.domain,
    startTime: item.start_time, durationMinutes: item.duration_minutes,
    constraintKind: item.constraint_kind, repeatKind: item.repeatKind,
    protected: Boolean(item.protected), goalId: item.goalId || "", status: item.completion_status,
  } : {
    date, title: "", detail: "", domain: defaultDomain, startTime: "09:00",
    durationMinutes: 30, constraintKind: "flexible", repeatKind: "none",
    protected: false, goalId: defaultGoalId, status: "planned",
  }), [date, item, defaultDomain, defaultGoalId]);

  async function submit(event) {
    event.preventDefault();
    if (!backendConnected || saving) return;
    setSaving(true);
    setError("");
    try {
      await onSave({ ...draft, goalId: draft.goalId || null, durationMinutes: Number(draft.durationMinutes) }, item?.id);
      if (!item) setDraft((current) => ({ ...current, title: "", detail: "",
        constraintKind: "flexible", repeatKind: "none", protected: false, goalId: "" }));
      else onCancel();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  }

  const matchingGoals = goals.filter((goal) => goal.domain === draft.domain && goal.status === "active");
  return (
    <form className="daily-capture" onSubmit={submit}>
      <div className="section-line"><small>{item ? t("editDailyRecord") : `${t("addTo")} ${date}`}</small><b>{t("yourOwnData")}</b></div>
      <div className="daily-form-grid">
        <label>{t("taskName")}<input required maxLength="200" value={draft.title || ""} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
        <label>{t("area")}<select value={draft.domain || "life"} onChange={(event) => setDraft({ ...draft, domain: event.target.value, goalId: "" })}>{Object.entries(domainMeta).map(([key]) => <option key={key} value={key}>{t(key)}</option>)}</select></label>
        <div className="fixed-date"><small>{t("date")}</small><strong>{date}</strong><span>{t("goalConnectionHelp")}</span></div>
        <label>{t("time")}<input required type="time" value={draft.startTime || "09:00"} onChange={(event) => setDraft({ ...draft, startTime: event.target.value })} /></label>
        <label>{t("minutes")}<input required type="number" min="1" max="1440" value={draft.durationMinutes || 30} onChange={(event) => setDraft({ ...draft, durationMinutes: event.target.value })} /></label>
        <label>{t("kind")}<select value={draft.constraintKind || "flexible"} onChange={(event) => setDraft({ ...draft, constraintKind: event.target.value })}><option value="flexible">{t("flexibleTask")}</option><option value="fixed">{t("fixedCommitment")}</option></select></label>
        <label>{t("repeat")}<select value={draft.repeatKind || "none"} onChange={(event) => setDraft({ ...draft, repeatKind: event.target.value })}><option value="none">{t("oneTime")}</option><option value="daily">{t("everyDay")}</option><option value="weekly">{t("everyWeek")}</option></select></label>
        <label className="goal-link-field">{t("relatedGoal")}<select value={draft.goalId || ""} onChange={(event) => setDraft({ ...draft, goalId: event.target.value })}><option value="">{t("noGoal")}</option>{matchingGoals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select><small>{t("goalConnectionHelp")}</small></label>
        <label className="detail-field">{t("details")}<input maxLength="1000" value={draft.detail || ""} onChange={(event) => setDraft({ ...draft, detail: event.target.value })} /></label>
        <label className="protected-field"><input type="checkbox" checked={Boolean(draft.protected)} onChange={(event) => setDraft({ ...draft, protected: event.target.checked })} /> {t("protectedHelp")}</label>
      </div>
      <div className="form-actions"><button disabled={!backendConnected || !draft.title?.trim() || saving}>{saving ? t("saving") : item ? t("saveChanges") : t("addDailyItem")}</button>{item && <button type="button" onClick={onCancel}>{t("cancel")}</button>}{!backendConnected && <span>{t("startServiceSave")}</span>}{error && <span role="alert">{error}</span>}</div>
    </form>
  );
}

/** Show user-authored daily records independently of proposed plan snapshots. */
function DayItemLedger({ day, onSave, onStatus, onRemove = null, backendConnected, domain = null, readOnly = false, reportable = true }) {
  const { t, demoText } = useI18n();
  const [editing, setEditing] = useState(null);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState(null);
  useEffect(() => { setEditing(null); setAdding(false); setRemoving(null); }, [day.date]);
  const items = domain ? day.dayItems.filter((item) => item.domain === domain || (domain === "life" && item.domain === "rest")) : day.dayItems;
  return (
    <section className="daily-ledger">
      <div className="section-line"><small>{domain ? t("allTasks") : t("dailyRecords")} / {day.date}</small>{readOnly ? <b>{t("readOnlyHistory")}</b> : <button onClick={() => { setAdding((value) => !value); setEditing(null); }}>{adding ? t("cancel") : t("addItem")}</button>}</div>
      {items.length ? items.map((item) => {
        const linkedGoal = day.goals.find((goal) => goal.id === item.goalId);
        return <div className={`managed-entry ${linkedGoal ? "has-goal" : ""}`} key={item.id}>
        <time>{item.start_time}</time><div className="managed-entry-copy"><strong>{day.demoMode ? demoText(item.title) : item.title}</strong><small>{t(item.domain)} · {t(item.constraint_kind)}{item.repeatKind !== "none" && ` · ${t(item.repeatKind)}`}</small>{linkedGoal ? <div className={`managed-goal domain-${linkedGoal.domain}`}><div className="managed-goal-title"><Target aria-hidden="true" /><span><small>{t("goalLinked")}</small><b>{day.demoMode ? demoText(linkedGoal.title) : linkedGoal.title}</b></span></div><GoalProgress goal={linkedGoal} compact /></div> : <small className="independent-label">{t("independentTask")}</small>}{item.originKind === "agent-origin" && <small className="origin-evidence">{day.demoMode ? demoText(item.originDetail) : item.originDetail}</small>}</div>
        <label className="visually-hidden" htmlFor={`status-${item.id}`}>{t("progressFor")} {day.demoMode ? demoText(item.title) : item.title}</label>
        <select id={`status-${item.id}`} value={item.completion_status} disabled={!backendConnected || readOnly || !reportable} onChange={(event) => onStatus(item, event.target.value).catch(() => {})}><option value="planned">{t("planned")}</option><option value="done">{t("done")}</option><option value="partial">{t("partial")}</option><option value="skipped">{t("skipped")}</option></select>
        {!readOnly && <div className="entry-actions">
          <button onClick={() => { setEditing(item); setAdding(false); }}>{t("edit")}</button>
          {onRemove && (removing === item.id
            ? <><button className="confirm-remove" onClick={() => { setRemoving(null); onRemove(item).catch(() => {}); }}>{t("confirmRemove")}</button><button onClick={() => setRemoving(null)}>{t("cancel")}</button></>
            : <button disabled={!backendConnected} onClick={() => setRemoving(item.id)}>{t("remove")}</button>)}
        </div>}
      </div>;
      }) : <p className="empty-copy">{t("noItems")}{!readOnly && t("addRealTask")}</p>}
      {!readOnly && (adding || editing) && <DayItemForm date={day.date} goals={day.goals} item={editing} defaultDomain={domain || "life"} onSave={onSave} backendConnected={backendConnected} onCancel={() => setEditing(null)} />}
    </section>
  );
}

/** Manage durable goals and their completion from user-recorded daily items. */
function GoalProgress({ goal, compact = false }) {
  const { t } = useI18n();
  const total = Number(goal.itemCount || 0);
  const done = Number(goal.doneCount || 0);
  const percent = total ? Math.round((done / total) * 100) : 0;
  return <div className={`goal-progress ${compact ? "compact" : ""}`}>
    <div><span style={{ width: `${percent}%` }} /></div>
    <small>{done}/{total} {t("linkedTasks")} · {percent}%</small>
  </div>;
}

function GoalTaskList({ goal, demoMode = false }) {
  const { t, demoText } = useI18n();
  return <div className="goal-task-list">
    <small>{t("goalTasks")}</small>
    {goal.linkedItems?.length ? goal.linkedItems.map((item) => <div key={item.id} className="goal-task-row">
      <span className={`task-status status-${item.status}`} />
      <span><strong>{demoMode ? demoText(item.title) : item.title}</strong><small>{item.date} · {item.startTime} · {item.durationMinutes}m</small></span>
      <b>{t(item.status)}</b>
    </div>) : <p className="empty-copy">{t("noGoalTasks")}</p>}
  </div>;
}

function GoalsPage({ day, onSave, onItemSave, onRemove = null, backendConnected, onToday }) {
  const { t, demoText } = useI18n();
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("learning");
  const [editing, setEditing] = useState(null);
  const [editedTitle, setEditedTitle] = useState("");
  const [removing, setRemoving] = useState(null);
  const [error, setError] = useState("");
  async function create(event) {
    event.preventDefault();
    if (!title.trim()) return;
    try {
      setError("");
      await onSave(null, { title: title.trim(), domain });
      setTitle("");
    } catch (caught) { setError(caught.message); }
  }
  return <main className="workbench-page goals-page">
    <header className="workbench-header"><small>DAYWRIGHT / {t("goalManagement")}</small><span>{backendConnected ? t("localPrivate") : t("previewMode")}</span></header>
    <div className="overview-hero"><div><small>{t("longerHorizon")}</small><h1>{t("goals")}</h1><p>{t("goalsIntro")}</p></div><button onClick={onToday}>{t("today")} →</button></div>
    <div className="goals-layout"><section className="goals-ledger"><div className="section-line"><small>{t("yourGoals")}</small><b>{day.goals.length} {t("recorded")}</b></div>
      {day.goals.length ? day.goals.map((goal) => <div className="goal-entry" key={goal.id}>
        <span className={`goal-area domain-${goal.domain}`}>{t(goal.domain).toUpperCase()}</span>
        <div className="goal-entry-main"><small>{t("goalPath")}</small><strong>{day.demoMode ? demoText(goal.title) : goal.title}</strong><GoalProgress goal={goal} />{editing === goal.id && <form onSubmit={async (event) => { event.preventDefault(); try { setError(""); await onSave(goal.id, { title: editedTitle, status: goal.status }); setEditing(null); } catch (caught) { setError(caught.message); } }}><input required maxLength="200" value={editedTitle} onChange={(event) => setEditedTitle(event.target.value)} /><button>{t("saveName")}</button></form>}<GoalTaskList goal={goal} demoMode={day.demoMode} /><details className="goal-task-capture"><summary>{t("addGoalTask")}</summary><DayItemForm date={day.date} goals={day.goals} defaultDomain={goal.domain} defaultGoalId={goal.id} onSave={onItemSave} backendConnected={backendConnected} onCancel={() => {}} /></details></div>
        <select aria-label={`${t("goals")}: ${goal.title}`} disabled={!backendConnected} value={goal.status} onChange={async (event) => { try { setError(""); await onSave(goal.id, { title: goal.title, status: event.target.value }); } catch (caught) { setError(caught.message); } }}><option value="active">{t("active")}</option><option value="paused">{t("paused")}</option><option value="completed">{t("completed")}</option></select>
        <div className="entry-actions">
          <button onClick={() => { setEditing(goal.id); setEditedTitle(goal.title); }}>{t("edit")}</button>
          {onRemove && (removing === goal.id
            ? <><button className="confirm-remove" onClick={async () => { setRemoving(null); try { setError(""); await onRemove(goal); } catch (caught) { setError(caught.message); } }}>{t("confirmRemove")}</button><button onClick={() => setRemoving(null)}>{t("cancel")}</button></>
            : <button disabled={!backendConnected} onClick={() => setRemoving(goal.id)}>{t("remove")}</button>)}
        </div>
      </div>) : <p className="empty-copy">{t("noGoals")}</p>}
    </section><form className="goal-capture" onSubmit={create}><small>{t("setGoal")}</small><label>{t("whatMatters")}<input required maxLength="200" value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>{t("area")}<select value={domain} onChange={(event) => setDomain(event.target.value)}>{Object.keys(domainMeta).map((key) => <option key={key} value={key}>{t(key)}</option>)}</select></label><button disabled={!backendConnected || !title.trim()}>{t("addGoal")}</button>{!backendConnected && <p>{t("startServiceGoals")}</p>}{error && <p role="alert">{error}</p>}</form></div>
  </main>;
}

function TodayPage({ day, reports, pool, onCalendar, onPlans, onGoals, onDomain, onDiscardAdvice, onClearAdviceWeek, onPlanStatus, backendConnected }) {
  const { t, language, demoText } = useI18n();
  const parts = dateParts(day.date, language);
  const activeGoals = day.goals.filter((goal) => goal.status === "active");
  const hasActivePlan = Boolean(day.confirmedVariantId);
  const workItems = hasActivePlan ? day.entries : [];
  const finishedItems = workItems.filter((item) => item.completion_status === "done").length;
  const remainingItems = workItems.filter((item) => !["done", "skipped"].includes(item.completion_status));
  const nextItem = [...remainingItems].sort((a, b) => a.start_time.localeCompare(b.start_time))[0];
  const totalMinutes = workItems.reduce((total, item) => total + item.duration_minutes, 0);
  const areaMinutes = Object.fromEntries(Object.keys(domainMeta).map((domain) => [domain, workItems.filter((item) => item.domain === domain).reduce((total, item) => total + item.duration_minutes, 0)]));
  const completion = workItems.length ? Math.round((finishedItems / workItems.length) * 100) : 0;
  const protectedCount = hasActivePlan ? day.dayItems.filter((item) => item.protected).length : 0;
  return (
    <main className="workbench-page today-page">
      <header className="workbench-header"><small>DAYWRIGHT / {t("dailyManagement")}</small><span>{backendConnected ? t("localPrivate") : t("previewMode")}</span></header>
      {day.demoMode && <div className="demo-banner"><b>{t("demoWorkspace")}</b><span>{t("demoCopy")}</span></div>}
      <div className="overview-hero">
        <div><small>{parts.monthYear.toUpperCase()} · {t("lifeLedger")}</small><h1>{t("todayTitle")}<span> / {parts.dayNumber}</span></h1><p>{t("todayIntro")}</p></div>
        <button onClick={onCalendar}>{t("openCalendar")} <ChevronRight aria-hidden="true" /></button>
      </div>
      {day.planSource === "deterministic-v1" && <div className="legacy-warning" role="note"><strong>{t("examplePlan")}</strong><span>{t("examplePlanHelp")}</span></div>}
      {!day.goals.length && !day.dayItems.length && !day.planSetId && <div className="welcome-management"><Target aria-hidden="true" /><div><strong>{t("startRealLife")}</strong><p>{t("startRealLifeHelp")}</p></div><button onClick={onGoals}>{t("firstGoal")}</button></div>}
      <section className="today-command" aria-label={t("commandCenter")}>
        <div className="command-heading"><div><small>{t("commandCenter")}</small><h2>{t("needsAttention")}</h2></div><div><button onClick={onPlans}>{t("plans")}</button><button onClick={onGoals}>{t("goals")}</button></div></div>
        <div className="today-command-grid">
          <article className="command-panel command-focus"><small>{t("nextUp")}</small>{nextItem ? <><time>{timeRange(nextItem.start_time, nextItem.duration_minutes)}</time><strong>{day.demoMode ? demoText(nextItem.title) : nextItem.title}</strong><p>{t(nextItem.domain)} · {t(nextItem.constraint_kind)}</p></> : hasActivePlan ? <><strong>{t("dayClear")}</strong><p>{t("dayClearHelp")}</p></> : <><strong>{t("noActivePlan")}</strong><p>{t("noActivePlanHelp")}</p></>}</article>
          <article className="command-panel command-state"><small>{t("dayControl")}</small><div><span><b>{day.confirmedVariantId ? t("live") : day.planSetId ? t("draft") : t("none")}</b>{t("todaysPlan")}</span><span><b>{completion}%</b>{t("dayProgress")}</span><span><b>{formatDuration(totalMinutes)}</b>{t("plannedTime")}</span><span><b>{protectedCount}</b>{t("protectedItems")}</span></div><button onClick={onPlans}>{day.planSetId ? t("reviewSchedule") : t("proposePlans")}</button></article>
          <article className="command-panel command-balance"><small>{t("areaBalance")}</small>{Object.entries(areaMinutes).map(([domain, minutes]) => <div key={domain}><span><b style={{ color: domainMeta[domain].color }}>{t(domain)}</b>{formatDuration(minutes)}</span><i><span style={{ width: `${totalMinutes ? Math.round((minutes / totalMinutes) * 100) : 0}%`, background: domainMeta[domain].color }} /></i></div>)}</article>
        </div>
        <div className="goal-pulse"><small>{t("goalPulse")}</small>{activeGoals.slice(0, 3).map((goal) => <button key={goal.id} onClick={() => onDomain(goal.domain === "rest" ? "life" : goal.domain)}><span><b>{t(goal.domain)}</b><strong>{day.demoMode ? demoText(goal.title) : goal.title}</strong></span><GoalProgress goal={goal} compact /></button>)}</div>
        <SummaryPanel reports={reports} pool={pool} date={day.date} compact embedded />
        <SuggestionPoolPanel pool={pool} onDiscard={onDiscardAdvice} onClearWeek={onClearAdviceWeek} />
      </section>
      {hasActivePlan ? <section className="today-active-plan"><div className="section-line"><small>{t("activeSchedule")} / {day.date}</small><b>{t("confirmed")}</b></div><Schedule entries={day.entries} onUpdate={onPlanStatus} canReport={backendConnected} title={t("timedItems")} showTimeRange /></section> : <section className="today-no-plan"><Target aria-hidden="true" /><div><small>{day.planSetId ? t("draft") : t("none")}</small><strong>{t("noActivePlan")}</strong><p>{day.planSetId ? t("draftNotActiveHelp") : t("noActivePlanHelp")}</p></div><button onClick={onPlans}>{day.planSetId ? t("reviewSchedule") : t("proposePlans")}</button></section>}
    </main>
  );
}

function CalendarPage({ month, days, day, today, onMonth, onSelect, onToday, onPlans, onDomain, onUpdate, onItemSave, onItemStatus, onItemRemove, onBuild, backendConnected }) {
  const { t, language, demoText } = useI18n();
  const records = new Map(days.map((item) => [item.date, item]));
  const dates = calendarDates(month);
  const recordedCount = days.length;
  const confirmedCount = days.filter((item) => item.confirmed).length;
  const doneCount = days.reduce((total, item) => total + item.doneCount, 0);
  const entryCount = days.reduce((total, item) => total + item.entryCount, 0);
  const managedCount = days.reduce((total, item) => total + item.managedCount, 0);
  const recentPlans = days.filter((item) => item.confirmed && item.date < today).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 5);
  return (
    <main className="workbench-page calendar-page">
      <header className="workbench-header"><small>DAYWRIGHT / {t("calendarManagement")}</small><span>{backendConnected ? t("recordedHistory") : t("previewMode")}</span></header>
      <div className="calendar-title"><div><small>{t("historyManagement")}</small><h1>{monthTitle(month, language)}</h1></div><div className="month-actions"><button aria-label={t("previousMonth")} onClick={() => onMonth(shiftMonth(month, -1))}><ChevronLeft aria-hidden="true" /></button><button onClick={onToday}>{t("today")}</button><button aria-label={t("nextMonth")} onClick={() => onMonth(shiftMonth(month, 1))}><ChevronRight aria-hidden="true" /></button><label>{t("jumpDate")}<input type="date" value={day.date} onChange={(event) => event.target.value && onSelect(event.target.value)} /></label></div></div>
      <div className="month-summary" aria-label={`${t("monthSummary")} ${monthTitle(month, language)}`}><small>{t("monthSummary")} <b>{t("recordedOnly")}</b></small><span><b>{recordedCount}</b> {t("daysWithRecords")}</span><span><b>{confirmedCount}</b> {t("confirmedPlans")}</span><span><b>{doneCount}/{entryCount}</b> {t("doneScheduled")}</span><span><b>{managedCount}</b> {t("userItems")}</span></div>
      {recentPlans.length > 0 && <div className="past-plan-strip"><small>{t("pastPlans")}</small>{recentPlans.map((record) => <button key={record.date} onClick={() => onSelect(record.date)}><b>{dateParts(record.date, language).day} {dateParts(record.date, language).dayNumber}</b><span>{demoText(record.variantName) || t("savedPlan")} · {record.doneCount}/{record.entryCount} {t("done")}</span></button>)}</div>}
      <div className="calendar-layout">
        <section className="month-sheet" aria-label={`${monthTitle(month, language)} ${t("calendar")}`}>
          <div className="weekday-head">{["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map((label) => <span key={label}>{t(label)}</span>)}</div>
          <div className="month-grid">{dates.map((date) => {
            const record = records.get(date);
            return <button key={date} className={`month-day ${date.slice(0, 7) !== month ? "outside" : ""} ${date === day.date ? "selected" : ""} ${date === today ? "is-today" : ""}`} onClick={() => onSelect(date)} aria-label={`${date}${record ? `, ${record.confirmed ? "confirmed plan" : record.planSource ? "draft plan" : "daily records"}, ${record.doneCount} of ${record.entryCount} done` : ", no recorded history"}`} aria-current={date === day.date ? "date" : undefined}>
              <b>{Number(date.slice(-2))}</b>{record && <span className={record.confirmed ? "confirmed-mark" : "draft-mark"}>{record.confirmed ? t("plan") : record.planSource ? t("draft") : t("recordedLabel")}<i>{record.doneCount}/{record.entryCount}</i></span>}
            </button>;
          })}</div>
          <p className="month-legend"><span /> {t("calendarLegend")}</p>
        </section>
        <aside className="calendar-detail">
          <div className="section-line"><small>{t("selectedDay")}</small><b>{day.date}</b></div>
          <h2>{dateParts(day.date, language).day} / {dateParts(day.date, language).dayNumber}</h2>
          <DaySummary day={day} />
          {day.planSource === "deterministic-v1" && <p className="legacy-warning">{t("olderPrototype")}</p>}
          {day.planSetId ? <>
            <p className="calendar-plan-note">{day.date !== today ? t("savedReadOnly") : day.confirmedVariantId ? t("confirmedShared") : t("draftReporting")}</p>
            <button className="text-link" onClick={onPlans}>{day.date !== today ? t("viewSavedPlan") : day.confirmedVariantId ? t("reviewPlan") : t("choosePlan")} →</button>
            <div className="calendar-area-links">{["learning", "life", "finance"].map((domain) => <button key={domain} onClick={() => onDomain(domain)}>{t(domain)} →</button>)}</div>
          </> : <><p className="empty-copy">{day.dayItems.length ? t("recordsNoPlan") : day.date < today ? t("pastNoPlanRetro") : day.date > today ? t("futureNoPlan") : t("noHistory")}</p>{day.date === today && day.dayItems.length > 0 && <button className="text-link" onClick={onBuild}>{t("proposePlans")}</button>}</>}
        </aside>
      </div>
      {day.date < today && <>
        <DayItemLedger day={day} onSave={onItemSave} onStatus={onItemStatus} onRemove={onItemRemove} backendConnected={backendConnected} readOnly reportable={false} />
        {day.entries.length > 0 && <section className="calendar-schedule"><div className="section-line"><small>{t("localPlanSnapshot")} / {day.date}</small><b>{t("readOnlyHistory")}</b></div><Schedule entries={day.entries} onUpdate={onUpdate} canReport={false} title={t("scheduledItems")} /></section>}
      </>}
    </main>
  );
}

function BalanceRow({ domain, minutes }) {
  const { t } = useI18n();
  const meta = domainMeta[domain];
  return (
    <div className="balance-row">
      <strong style={{ color: meta.color }}>{t(domain).toUpperCase()}</strong>
      <span>{formatDuration(minutes)}</span><i>—</i><small>{t(meta.statement.replace(" ", ""))}</small>
    </div>
  );
}

/** Keep comparison, schedule, rationale, and confirmation on one management surface. */
function PlanDesk({ day, reports, readOnly, onVariant, onConfirm, onReplace, onCancelReplace, replacing, onChat, backendConnected }) {
  const { t, demoText } = useI18n();
  const selected = day.variants.find((variant) => variant.id === day.selectedVariantId) || day.variants[0];
  const confirmed = day.confirmedVariantId === day.selectedVariantId;
  const confirmedName = day.variants.find((variant) => variant.id === day.confirmedVariantId)?.name;
  return (
    <main className="workbench-page plan-desk">
      <header className="workbench-header"><small>DAYWRIGHT / {t("planManagement")}</small><span>{backendConnected ? t("localPlanSnapshot") : t("previewMode")}</span></header>
      <div className="plan-desk-heading"><div><small>{day.date} · {readOnly ? t("readOnlyHistory") : confirmed ? t("current") : t("previewOnly")}</small><h1>{readOnly ? t("dayPreserved") : t("plansHeading")}</h1><p>{readOnly ? t("pastPlanHelp") : t("plansIntro")}</p></div><span className={`model-dot ${day.model?.running ? "running" : ""}`} title={day.model?.label} /></div>
      {day.planSource === "deterministic-v1" && <div className="legacy-warning"><strong>{t("prototypeExample")}</strong><span>{t("prototypeExampleHelp")}</span></div>}
      <div className="plan-choice"><div className="section-line"><small>{readOnly ? t("savedPastPlan") : t("planAlternatives")}</small><b>{confirmedName ? `${demoText(confirmedName).toUpperCase()} · ${t("currentConfirmed")}` : t("notConfirmed")}</b></div>{!readOnly && <div className="variant-tabs" aria-label={t("planAlternatives")}>{day.variants.map((variant) => <button className={variant.id === day.selectedVariantId ? "active" : ""} key={variant.id} onClick={() => onVariant(variant.id)} aria-pressed={variant.id === day.selectedVariantId}>{demoText(variant.name)}{variant.id === day.confirmedVariantId && <small>✓ {t("current")}</small>}</button>)}</div>}<p>{demoText(selected.rationale)}</p></div>
      <AgentTrail route={day.planRoute} />
      <div className="plan-overview"><div><small>{t("allocation")}</small>{Object.entries(day.balance).map(([domain, minutes]) => <BalanceRow domain={domain} minutes={minutes} key={domain} />)}</div><div><small>{t("fixedCommitments")}</small>{day.hardConstraints.length ? day.hardConstraints.map((constraint) => <p key={constraint}>{demoText(constraint)}</p>) : <p>{t("noFixed")}</p>}</div><div><small>{t("plannerNotes")}</small>{day.plannerNotes.map((note) => <p key={note}>{demoText(note)}</p>)}</div></div>
      <div className="section-line"><small>{t("schedule")} / {demoText(selected.name).toUpperCase()}</small><b>{confirmed ? t("current") : t("previewOnly")}</b></div><Schedule entries={day.entries} title={t("timedItems")} />
      {readOnly ? <SummaryPanel reports={reports} date={day.date} /> : <><div className="plan-decision"><div><small>{t("decisionFile")}</small><strong>{confirmed ? t("currentConfirmed") : confirmedName ? `${t("current")}: ${demoText(confirmedName)}` : t("nothingChanges")}</strong><p>{t("completionExplicit")}</p></div><div><button className="confirm-button" onClick={onConfirm} disabled={confirmed || replacing || !backendConnected}>{confirmed ? t("currentConfirmed") : confirmedName ? t("reviewReplacement") : t("confirmPlan")}</button><button onClick={() => onChat("adjust")}>{t("markAgents")}</button></div></div>{replacing && <div className="replace-review" role="group"><button onClick={onReplace}>{t("reviewReplacement")}</button><button onClick={onCancelReplace}>{t("cancel")}</button></div>}</>}
    </main>
  );
}

function EmptyPlanDesk({ day, today, onBuild, onSave, onStatus, onRemove, backendConnected }) {
  const { t } = useI18n();
  const past = day.date < today;
  return <main className="workbench-page plan-desk">
    <header className="workbench-header"><small>DAYWRIGHT / {t("planManagement")}</small></header>
    <div className="overview-hero"><div><small>{day.date} · {t("yourRecordsFirst")}</small><h1>{past ? t("noPlanSaved") : t("noPlan")}</h1><p>{past ? t("pastNoPlan") : day.date > today ? t("futurePlanHelp") : day.dayItems.length ? t("noPlanIntro") : t("addItemsFirst")}</p></div>{day.date === today && <button disabled={!backendConnected} onClick={onBuild}>{t("proposePlans")}</button>}</div>
    <DayItemLedger day={day} onSave={onSave} onStatus={onStatus} onRemove={onRemove} backendConnected={backendConnected} readOnly={past} reportable={day.date === today} />
  </main>;
}

function ConversationDrawer({ open, onClose, day, mode, setMode, onSent, backendConnected }) {
  const { language, t, demoText } = useI18n();
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState(day.messages || []);
  const [proposal, setProposal] = useState(null);
  const listRef = useRef(null);
  const captureRef = useRef(null);
  const [voiceState, setVoiceState] = useState("idle");
  const [voiceError, setVoiceError] = useState("");

  useEffect(() => setMessages(day.messages || []), [day.messages]);
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, proposal]);
  useEffect(() => {
    if (open || !captureRef.current) return;
    const capture = captureRef.current;
    captureRef.current = null;
    capture.stop().catch(() => {});
    setVoiceState("idle");
  }, [open]);

  async function toggleVoice() {
    if (!backendConnected || day.voice?.state !== "available") return;
    setVoiceError("");
    if (!captureRef.current) {
      setVoiceState("starting");
      try {
        captureRef.current = await beginVoiceCapture();
        setVoiceState("recording");
      } catch (caught) {
        setVoiceError(caught.message);
        setVoiceState("idle");
      }
      return;
    }
    const capture = captureRef.current;
    captureRef.current = null;
    setVoiceState("transcribing");
    try {
      const clip = await capture.stop();
      const result = await api("/api/voice/transcribe", {
        method: "POST", headers: { "Content-Type": "audio/wav" }, body: clip,
      });
      setMessage((current) => current ? `${current.trim()} ${result.text}` : result.text);
      setVoiceState("recognized");
    } catch (caught) {
      setVoiceError(caught.message);
      setVoiceState("idle");
    }
  }

  async function send(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || sending) return;
    setMessage("");
    setSending(true);
    const optimistic = { id: `local-${Date.now()}`, role: "user", content: trimmed, mode };
    setMessages((current) => [...current, optimistic]);
    try {
      if (!backendConnected) {
        setMessages((current) => [...current, { id: `offline-${Date.now()}`, role: "assistant", mode, content: "The local service is unavailable. This message was not sent or saved; start the service to talk to the agents." }]);
        return;
      }
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ date: day.date, message: trimmed, mode, selectedVariantId: day.selectedVariantId, language }),
      });
      setMessages((current) => [...current, result.assistantMessage]);
      setProposal(result.proposedAction);
      onSent(result.model);
    } catch (error) {
      setMessages((current) => [...current, { id: `error-${Date.now()}`, role: "assistant", mode, content: error.message }]);
    } finally {
      setSending(false);
    }
  }

  async function decide(decision) {
    if (!proposal || !backendConnected) {
      setProposal(null);
      return;
    }
    try {
      await api(`/api/actions/${proposal.id}`, { method: "POST", body: JSON.stringify({ decision }) });
      setProposal(null);
      if (decision === "confirmed") onSent(null, proposal.payload.variantId, proposal.payload.date);
    } catch (caught) {
      setMessages((current) => [...current, { id: `error-${Date.now()}`, role: "assistant", mode, content: caught.message }]);
    }
  }

  return (
    <div className={`conversation-layer ${open ? "open" : ""}`} aria-hidden={!open}>
      <button className="conversation-scrim" onClick={onClose} aria-label={t("close")} tabIndex={open ? 0 : -1} />
      <aside className="conversation-drawer" role="dialog" aria-modal="true" aria-label={t("talk")}>
        <header>
          <div><small>{t("agentWorkbench")}</small><h2>{t("talkTitle")}</h2></div>
          <button onClick={onClose} aria-label={t("close")}><Icon name="close" /></button>
        </header>
        <div className="model-card">
          <span className={`model-dot ${day.model?.running ? "running" : ""}`} />
          <div><strong>{t("agentModel")}</strong><small>{day.model?.label || t("localAi")} · {day.rag?.vectorStore?.sourceCount || 0} {t("indexedSources")}</small></div>
          <b>{t("private")}</b>
        </div>
        <div className="mode-switcher">
          {Object.entries(modeCopy).map(([id]) => (
            <button key={id} className={mode === id ? "active" : ""} onClick={() => setMode(id)}>{t(id)}</button>
          ))}
        </div>
        <p className="mode-help">{t(`${mode}Help`)}</p>
        <div className="message-list" ref={listRef} aria-live="polite">
          {messages.length === 0 && (
            <div className="opening-message">
              <Icon name="spark" />
              <p><strong>{t("roomToBreathe")}</strong> {t("orchestratorHelp")}</p>
            </div>
          )}
          {messages.map((item) => (
            <div className={`message ${item.role}`} key={item.id}>
              <small>{item.role === "user" ? t("you") : "DAYWRIGHT"}</small><p>{day.demoMode ? demoText(item.content) : item.content}</p>
              {item.role === "assistant" && <RetrievalTrail retrieval={item.retrieval} />}
              {item.role === "assistant" && <AgentTrail route={item.agentRoute} />}
            </div>
          ))}
          {sending && <div className="message assistant thinking"><small>{t("orchestrator")}</small><p>{t("consulting")}</p></div>}
          {proposal && (
            <div className="proposal-card">
              <small>{t("proposedChange")}</small><strong>{demoText(proposal.payload.variantName || proposal.actionType)}</strong><p>{demoText(proposal.explanation)}</p>
              <div><button onClick={() => decide("confirmed")}>{t("confirmChange")}</button><button onClick={() => decide("dismissed")}>{t("keepCurrent")}</button></div>
            </div>
          )}
        </div>
        <form className="composer" onSubmit={send}>
          <button type="button" className={`mic-button ${voiceState === "recording" ? "recording" : ""}`} onClick={toggleVoice} disabled={!backendConnected || day.voice?.state !== "available" || sending || voiceState === "starting" || voiceState === "transcribing"} aria-label={voiceState === "recording" ? "Stop push-to-talk and transcribe locally" : "Start push-to-talk recording"} aria-pressed={voiceState === "recording"} title={day.voice?.state === "available" ? "Push to talk; press again to transcribe on this Mac" : day.voice?.label || "Local Whisper speech runtime needs setup"}><Icon name="mic" /></button>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={mode === "adjust" ? t("adjustPlaceholder") : t("askPlaceholder")}
            rows="2"
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send(event);
              }
            }}
          />
          <button className="send-button" type="submit" disabled={!message.trim() || sending} aria-label={t("send")}><Icon name="send" /></button>
        </form>
        <p className="voice-status" role="status">{voiceError || (voiceState === "recording" ? t("voiceRecording") : voiceState === "starting" ? t("voiceStarting") : voiceState === "transcribing" ? t("voiceTranscribing") : voiceState === "recognized" ? t("voiceRecognized") : day.voice?.state === "available" ? t("voiceReady") : day.voice?.label || t("voiceSetup"))}</p>
        <p className="composer-footnote">{t("proposalControl")}</p>
      </aside>
    </div>
  );
}

function KnowledgeCapture({ backendConnected, onSaved }) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!backendConnected || !title.trim() || !text.trim() || saving) return;
    setSaving(true);
    setError("");
    try {
      const source = await api("/api/knowledge/sources", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), sourceType: "note", text: text.trim() }),
      });
      setTitle("");
      setText("");
      await onSaved(source);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="knowledge-capture" onSubmit={submit}>
      <small>{t("addKnowledge")}</small>
      <label>{t("title")}<input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label>{t("text")}<textarea value={text} onChange={(event) => setText(event.target.value)} rows="5" /></label>
      {error && <p role="alert">{error}</p>}
      <button disabled={!backendConnected || !title.trim() || !text.trim() || saving}>{saving ? t("indexing") : t("indexNote")}</button>
    </form>
  );
}

function KnowledgeTopic({ backendConnected, onSaved }) {
  const { t } = useI18n();
  const [topic, setTopic] = useState("");
  const [explicitWeb, setExplicitWeb] = useState(false);
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState(null);
  const [pending, setPending] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!backendConnected) return;
    api("/api/knowledge/import-plans").then((response) => setPending(response.pending))
      .catch(() => setPending([]));
  }, [backendConnected]);

  async function search(event) {
    event.preventDefault();
    if (!backendConnected || !topic.trim() || searching) return;
    setSearching(true);
    setError("");
    setResult(null);
    try {
      const outcome = await api("/api/knowledge/topic", {
        method: "POST",
        body: JSON.stringify({ topic: topic.trim(), explicitWeb }),
      });
      setResult(outcome);
      setSelectedPlanId(outcome.importOptions?.plans[0]?.id || "");
      if (outcome.importOptions) setPending((items) => [outcome.importOptions, ...items]);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSearching(false);
    }
  }

  async function confirmImport() {
    if (!selectedPlanId || importing) return;
    setImporting(true);
    setError("");
    try {
      const accepted = await api(`/api/knowledge/import-plans/${selectedPlanId}/confirm`, {
        method: "POST",
      });
      setResult((current) => ({ ...current, publicFetch: "imported",
        source: accepted.source }));
      setPending((items) => items.filter((item) =>
        item.acquisitionId !== result.importOptions.acquisitionId));
      if (accepted.source) await onSaved(accepted.source);
    } catch (caught) { setError(caught.message); }
    finally { setImporting(false); }
  }

  const options = result?.importOptions;

  return <form className="knowledge-capture knowledge-topic" onSubmit={search}>
    <small>{t("findTopic")}</small>
    <label>{t("topic")}<input value={topic} maxLength={200} onChange={(event) => setTopic(event.target.value)} /></label>
    <label className="knowledge-web-choice"><input type="checkbox" checked={explicitWeb} onChange={(event) => setExplicitWeb(event.target.checked)} /> {t("fetchWeb")}</label>
    <p className="empty-copy">{t("topicPrivacy")}</p>
    {error && <p role="alert">{error}</p>}
    {result && <p role="status">{result.publicFetch === "awaiting_import_choice" ? t("publicFetched") : result.publicFetch === "imported" ? t("organizationIndexed") : result.publicFetch === "needs_general_topic" ? t("generalTopicNeeded") : result.retrieval?.status === "ready" ? t("foundLocal") : t("localUnavailable")}{result.source?.sourceUrl && <> · <a href={result.source.sourceUrl} target="_blank" rel="noopener noreferrer">{t("sourceAttribution")} ↗</a></>}</p>}
    <button disabled={!backendConnected || !topic.trim() || searching}>{searching ? t("searching") : explicitWeb ? t("localAndWeb") : t("findLocal")}</button>
    {pending.some((item) => item.acquisitionId !== options?.acquisitionId) && <div className="pending-topics"><small>{t("pendingImports")}</small>{pending.filter((item) => item.acquisitionId !== options?.acquisitionId).map((item) =>
      <button type="button" key={item.acquisitionId} onClick={() => {
        setResult({ publicFetch: "awaiting_import_choice", importOptions: item });
        setSelectedPlanId(item.selectedPlanId || item.plans[0]?.id || "");
        setTopic(item.topic);
      }}>{item.topic} · {t("reviewChoices")}</button>)}</div>}
    {options && result.publicFetch === "awaiting_import_choice" && <div className="import-choices">
      <small>{t("publicSource")} / <a href={options.sourceUrl} target="_blank" rel="noopener noreferrer">{options.sourceTitle} ↗</a> · {options.sourceLicense}</small>
      <p>{t("sourceFilterHelp")} {options.filter.timeliness}.</p>
      <p>{t("organizationHelp")}</p>
      {options.plans.map((plan) => <label className="import-choice" key={plan.id}>
        <input type="radio" name={`import-${options.acquisitionId}`} checked={selectedPlanId === plan.id}
          onChange={() => setSelectedPlanId(plan.id)} />
        <span><b>{plan.name}</b><small>{plan.labels.join(" / ")}</small></span>
      </label>)}
      <button type="button" onClick={confirmImport} disabled={!selectedPlanId || importing}>
        {importing ? t("indexing").toUpperCase() : t("confirmImport")}</button>
    </div>}
  </form>;
}

function LocalFileImport({ backendConnected, onSaved }) {
  const { t } = useI18n();
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  function choose(event) {
    const selected = event.target.files?.[0] || null;
    setFile(null);
    setSaved("");
    if (!selected) return;
    if (!/\.(md|markdown|pdf|docx)$/i.test(selected.name)) {
      setError("Choose Markdown (.md), PDF (.pdf), or Word (.docx); other formats are not supported.");
    } else if (selected.size > 2_000_000) {
      setError("Split this file first; local import supports files smaller than 2 MB.");
    } else {
      setError("");
      setFile(selected);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (!backendConnected || !file || saving) return;
    setSaving(true);
    setError("");
    try {
      const filename = btoa(String.fromCharCode(...new TextEncoder().encode(file.name)));
      const response = await fetch("/api/knowledge/import", {
        method: "POST", headers: { "Content-Type": "application/octet-stream",
          "X-DayWright-Filename": filename }, body: file,
      });
      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || `Local import failed (${response.status})`);
      }
      const source = await response.json();
      setSaved(`${source.title} indexed locally · ${source.chunkCount} chunk${source.chunkCount === 1 ? "" : "s"}`);
      setFile(null);
      await onSaved(source);
    } catch (caught) { setError(caught.message); }
    finally { setSaving(false); }
  }

  return <form className="knowledge-capture" onSubmit={submit}>
    <small>{t("importFile")}</small>
    <label>{t("chooseFile")}<input type="file" accept=".md,.markdown,.pdf,.docx" onChange={choose} /></label>
    <p className="empty-copy">{t("filePrivacy")}</p>
    {error && <p role="alert">{error}</p>}{saved && <p role="status">{saved}</p>}
    <button disabled={!backendConnected || !file || saving}>{saving ? t("extracting") : t("importSelected")}</button>
  </form>;
}

function DomainPage({ section, day, today, onToday, onCalendar, onGoals, onChat, onUpdate, onItemSave, onItemStatus, onItemRemove, backendConnected, onKnowledgeSaved, onAreaSaved }) {
  const { t } = useI18n();
  const sourceCount = day.rag?.vectorStore?.sourceCount || 0;
  const copy = {
    learning: [t("learningTitle"), t("learningIntro")],
    life: [t("lifeTitle"), t("lifeIntro")],
    finance: [t("moneyTitle"), t("moneyIntro")],
    library: [t("libraryTitle"), t("libraryIntro")],
  };
  const [title, description] = copy[section];
  const isArea = ["learning", "life", "finance"].includes(section);
  return (
    <main className={`workbench-page area-page area-${section}`}>
      <header className="workbench-header"><small>DAYWRIGHT / {t(section).toUpperCase()}</small><span>{backendConnected ? t("localPrivate") : t("previewMode")}</span></header>
      <div className="overview-hero"><div><small>{t("manageArea")} / {day.date}</small><h1>{title}</h1><p>{description}</p></div><button onClick={onCalendar}>{t("calendar")} →</button></div>
      {isArea ? <><section className="area-task-board"><div className="area-task-heading"><div><small>{t("dayLedger")}</small><h2>{t("allTasks")}</h2><p>{t("allTasksHelp")}</p></div><button onClick={onGoals}>{t("manageGoals")}</button></div><DayItemLedger day={day} domain={section} onSave={onItemSave} onStatus={onItemStatus} onRemove={onItemRemove} backendConnected={backendConnected} readOnly={day.date < today} reportable={day.date === today} /></section><DomainRecordsBoard key={`${section}-${day.date}`} domain={section} date={day.date} today={today} backendConnected={backendConnected} onSaved={onAreaSaved} demoMode={day.demoMode} /></> : <div className="library-management"><div><strong>{sourceCount} {t("indexedSources")}</strong><p>{t("libraryRagHelp")}</p><button onClick={() => onChat("ask")}>{t("talkSources")}</button></div><KnowledgeTopic backendConnected={backendConnected} onSaved={onKnowledgeSaved} /><LocalFileImport backendConnected={backendConnected} onSaved={onKnowledgeSaved} /><KnowledgeCapture backendConnected={backendConnected} onSaved={onKnowledgeSaved} /></div>}
      <button className="back-to-today" onClick={onToday}>← {t("today")}</button>
    </main>
  );
}

/** The place each workspace section belongs to in the four-place navigation. */
const PLACE_OF_TAB = {
  today: "today", plans: "today", calendar: "calendar", library: "library",
  goals: "records", learning: "records", life: "records", finance: "records",
};

/** Workspace sections shown inside Records. */
const RECORD_TABS = ["goals", "learning", "life", "finance"];

function DayWrightApp() {
  const workspace = useWorkspace();
  const {
    today, day, planPreview, month, calendarDays, reports, pool, backendConnected, replacing, notice,
    setReplacing, chooseMonth, selectVariant, confirm, applyConfirmation, updateEntry, discardAdvice,
    clearAdviceWeek, saveGoal, updateItemStatus, removeItem, removeGoal, handleConversationUpdate,
    handleKnowledgeSaved, handleAreaSaved,
  } = workspace;
  const [activeTab, setActiveTab] = useState("today");
  const lastRecordsRef = useRef("goals");
  if (RECORD_TABS.includes(activeTab)) lastRecordsRef.current = activeTab;
  const place = PLACE_OF_TAB[activeTab];
  const [conversationOpen, setConversationOpen] = useState(false);
  const [conversationMode, setConversationMode] = useState("ask");

  async function navigate(section) {
    setReplacing(false);
    setActiveTab(section);
    if (section === "today") await workspace.showToday();
    else if (section === "plans") workspace.reviewPlans();
  }

  function openPlans() {
    workspace.reviewPlans();
    setActiveTab("plans");
  }

  async function chooseDate(date) {
    setActiveTab("calendar");
    await workspace.showDate(date);
  }

  async function saveItem(payload, itemId = null) {
    if (await workspace.saveItem(payload, itemId)) setActiveTab("calendar");
  }

  async function buildPlan() {
    if (await workspace.buildPlan()) setActiveTab("plans");
  }

  function openConversation(mode = "ask") {
    setConversationMode(mode);
    setConversationOpen(true);
  }

  function goToPlace(next) {
    navigate(next === "records" ? lastRecordsRef.current : next);
  }

  function toggleTalk() {
    if (conversationOpen) setConversationOpen(false);
    else openConversation("ask");
  }

  useEffect(() => {
    function onKey(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        toggleTalk();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="dw-app">
      <TopBar place={place} onPlace={goToPlace} backendConnected={backendConnected} demoMode={Boolean(day.demoMode)} model={day.model} talkOpen={conversationOpen} onTalk={toggleTalk} />
      <PhoneHeader backendConnected={backendConnected} demoMode={Boolean(day.demoMode)} model={day.model} />
      <div className={`dw-main${place === "records" ? " dw-with-side" : ""}`}>
      {place === "records" && <RecordsNav section={activeTab} onSection={navigate} />}
      {activeTab === "today" ? (
        <TodayPage day={day} reports={reports} pool={pool} onCalendar={() => setActiveTab("calendar")} onPlans={openPlans} onGoals={() => navigate("goals")} onDomain={navigate} onDiscardAdvice={discardAdvice} onClearAdviceWeek={clearAdviceWeek} onPlanStatus={updateEntry} backendConnected={backendConnected} />
      ) : activeTab === "calendar" ? (
        <CalendarPage month={month} days={calendarDays} day={day} today={today} onMonth={chooseMonth} onSelect={chooseDate} onToday={() => chooseDate(today)} onPlans={openPlans} onDomain={navigate} onUpdate={updateEntry} onItemSave={saveItem} onItemStatus={updateItemStatus} onItemRemove={removeItem} onBuild={buildPlan} backendConnected={backendConnected} />
      ) : activeTab === "plans" ? (
        planPreview.planSetId ? <PlanDesk day={planPreview} reports={reports} readOnly={planPreview.date !== today} onVariant={selectVariant} onConfirm={confirm} onReplace={() => applyConfirmation(true)} onCancelReplace={() => setReplacing(false)} replacing={replacing} onChat={openConversation} backendConnected={backendConnected} /> : <EmptyPlanDesk day={day} today={today} onBuild={buildPlan} onSave={saveItem} onStatus={updateItemStatus} onRemove={removeItem} backendConnected={backendConnected} />
      ) : activeTab === "goals" ? (
        <GoalsPage day={day} onSave={saveGoal} onItemSave={saveItem} onRemove={removeGoal} backendConnected={backendConnected} onToday={() => navigate("today")} />
      ) : (
        <DomainPage section={activeTab} day={day} today={today} onToday={() => navigate("today")} onCalendar={() => setActiveTab("calendar")} onGoals={() => navigate("goals")} onChat={openConversation} onUpdate={updateEntry} onItemSave={saveItem} onItemStatus={updateItemStatus} onItemRemove={removeItem} backendConnected={backendConnected} onKnowledgeSaved={handleKnowledgeSaved} onAreaSaved={handleAreaSaved} />
      )}
      </div>
      <BottomBar place={place} onPlace={goToPlace} talkOpen={conversationOpen} onTalk={toggleTalk} />
      <ConversationDrawer
        open={conversationOpen}
        onClose={() => setConversationOpen(false)}
        day={activeTab === "plans" ? planPreview : day}
        mode={conversationMode}
        setMode={setConversationMode}
        onSent={handleConversationUpdate}
        backendConnected={backendConnected}
      />
      <Notice message={notice} />
    </div>
  );
}

export function App() {
  return <LanguageProvider><DayWrightApp /></LanguageProvider>;
}
