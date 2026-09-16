import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronLeft, ChevronRight, MessageSquare, Mic, Paperclip, Pin, Send, Sparkles, Target, X } from "lucide-react";
import { api, getCalendar, getDay, getSummaries } from "./api";
import { DomainRecordsBoard } from "./DomainRecords";
import { beginVoiceCapture } from "./voice";

const tabs = [
  ["today", "Today", "01"],
  ["calendar", "Calendar", "02"],
  ["plans", "Plans", "03"],
  ["learning", "Learn", "04"],
  ["life", "Life", "05"],
  ["finance", "Money", "06"],
  ["library", "Library", "07"],
  ["goals", "Goals", "08"],
];

const domainMeta = {
  learning: { label: "Learn", color: "#f1512e", statement: "steady progress" },
  life: { label: "Life", color: "#245fe5", statement: "moderate pace" },
  finance: { label: "Finance", color: "#24855f", statement: "on track" },
  rest: { label: "Rest", color: "#66615c", statement: "protected" },
};

const modeCopy = {
  ask: ["Ask", "Understand the plan or weigh a tradeoff."],
  adjust: ["Adjust", "Describe a change. Wellspent will propose it for confirmation."],
  report: ["Report", "Talk through what happened; completion remains explicit."],
};

function localToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function emptyDay(date) {
  return {
    date, planSetId: null, planSource: null, selectedVariantId: null,
    confirmedVariantId: null, variants: [], entries: [], suggestion: null,
    balance: { learning: 0, life: 0, finance: 0, rest: 0 },
    hardConstraints: [], plannerNotes: [], dayItems: [], goals: [], messages: [],
    model: { label: "Local model starts when you ask", running: false },
    rag: { vectorStore: { sourceCount: 0 } },
  };
}

function previewCalendarDay(day) {
  const variantId = day.confirmedVariantId || day.selectedVariantId;
  return {
    date: day.date,
    confirmed: Boolean(day.confirmedVariantId),
    variantName: day.variants.find((variant) => variant.id === variantId)?.name || null,
    planSource: day.planSource,
    entryCount: day.entries.length || day.dayItems.length,
    doneCount: (day.entries.length ? day.entries : day.dayItems).filter((entry) => entry.completion_status === "done").length,
    managedCount: day.dayItems.length,
    managedDoneCount: day.dayItems.filter((entry) => entry.completion_status === "done").length,
  };
}

function formatDuration(minutes) {
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}h ${String(remainder).padStart(2, "0")}m` : `${hours}h 00m`;
}

function dateParts(value) {
  const date = new Date(`${value}T12:00:00`);
  return {
    day: new Intl.DateTimeFormat("en", { weekday: "short" }).format(date).toUpperCase(),
    dayNumber: new Intl.DateTimeFormat("en", { day: "2-digit" }).format(date),
    monthYear: new Intl.DateTimeFormat("en", { month: "long", year: "numeric" }).format(date),
  };
}

function monthTitle(month) {
  return new Intl.DateTimeFormat("en", { month: "long", year: "numeric" }).format(new Date(`${month}-01T12:00:00`));
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
  if (!route?.length) return null;
  return (
    <div className="agent-trail" aria-label={`Agent route: ${route.map((run) => run.label).join(", ")}`}>
      <small>AGENT ROUTE</small>
      <div>
        {route.map((run, index) => (
          <span className={`agent-chip agent-${run.agentKey}`} key={`${run.agentKey}-${run.phase}-${index}`} title={run.summary}>
            <b>{String(index + 1).padStart(2, "0")}</b>{run.label}<i>{run.phase}</i>
          </span>
        ))}
      </div>
    </div>
  );
}

function RetrievalTrail({ retrieval }) {
  if (!retrieval?.matches?.length) return null;
  const sources = Array.from(
    new Map(retrieval.matches.map((match) => [match.sourceId, match])).values(),
  );
  return (
    <div className="retrieval-trail" aria-label={`Retrieved sources: ${sources.map((source) => source.sourceTitle).join(", ")}`}>
      <small>RETRIEVED SOURCES / SQLITE-VEC</small>
      <div>
        {sources.map((source) => (
          <span key={source.sourceId} title={source.content}>
            <b>{source.sourceType}</b>{source.sourceUrl ? <a href={source.sourceUrl} target="_blank" rel="noopener noreferrer">{source.sourceTitle} ↗</a> : source.sourceTitle}<i>chunk {source.chunkIndex + 1}{source.sourceLicense && ` · ${source.sourceLicense}`}</i>
          </span>
        ))}
      </div>
    </div>
  );
}

function TabRail({ active, onChange }) {
  return (
    <nav className="tab-rail" aria-label="Main sections">
      <div className="folio-mark" aria-label="Wellspent"><span>W/</span></div>
      <div className="paper-tabs">
        {tabs.map(([id, label, number]) => (
          <button
            className={`paper-tab tab-${id} ${active === id ? "active" : ""}`}
            key={id}
            onClick={() => onChange(id)}
            aria-current={active === id ? "page" : undefined}
          >
            <span className="tab-number">{number}</span>
            <span>{label}</span>
          </button>
        ))}
      </div>
      <p className="edge-note">A calmer<br />brighter<br />you <b>/</b></p>
    </nav>
  );
}

function StatusControl({ entry, onUpdate }) {
  const [open, setOpen] = useState(false);
  const labels = { planned: "Report", done: "Done", partial: "Partial", skipped: "Skipped" };
  return (
    <div className="status-control">
      <button
        className={`status-trigger status-${entry.completion_status}`}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={`Report status for ${entry.title}`}
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

function Schedule({ entries, onUpdate, canReport = false, title = "DAY SCHEDULE" }) {
  return (
    <section className="schedule" aria-labelledby="schedule-title">
      <div className="schedule-heading">
        <span>TIME</span><span id="schedule-title">{title}</span><span>AREA</span>
      </div>
      {entries.map((entry) => {
        const meta = domainMeta[entry.domain];
        const isBuffer = entry.title.toLowerCase().includes("buffer");
        return (
          <article
            className={`schedule-row domain-${entry.domain} ${isBuffer ? "buffer" : ""} completion-${entry.completion_status}`}
            key={entry.id}
          >
            <time>{entry.start_time}</time>
            <div className="task-copy">
              <span className="domain-rule" />
              <h3>{entry.title}</h3>
              <p>{entry.detail}</p>
              {entry.constraint_kind === "fixed" && <strong className="constraint"><Icon name="pin" /> FIXED</strong>}
              {isBuffer && <strong className="constraint flexible">FLEXIBLE</strong>}
              {canReport && <StatusControl entry={entry} onUpdate={onUpdate} />}
            </div>
            <div className="area-copy">
              <b style={{ color: meta.color }}>{meta.label.toUpperCase()}</b>
              <span>{formatDuration(entry.duration_minutes)}</span>
            </div>
          </article>
        );
      })}
    </section>
  );
}

function DaySummary({ day }) {
  const entries = day.planSetId ? day.entries : day.dayItems || [];
  const managed = day.dayItems || [];
  const done = entries.filter((entry) => entry.completion_status === "done").length;
  const partial = entries.filter((entry) => entry.completion_status === "partial").length;
  const skipped = entries.filter((entry) => entry.completion_status === "skipped").length;
  const planName = day.variants?.find((variant) => variant.id === day.confirmedVariantId)?.name;
  return (
    <section className="day-summary" aria-label={`Summary for ${day.date}`}>
      <div className="section-line"><small>DAY SCHEDULE / {day.date}</small><b>{day.confirmedVariantId ? `CONFIRMED · ${planName}` : day.planSetId ? "DRAFT · NOT CONFIRMED" : managed.length ? "RECORDED DAY · NO PLAN" : "NO TIMED ITEMS YET"}</b></div>
      <div className="summary-totals">
        <div><strong>{entries.length}</strong><span>scheduled</span></div>
        <div><strong>{done}</strong><span>done</span></div>
        <div><strong>{partial}</strong><span>partial</span></div>
        <div><strong>{skipped}</strong><span>skipped</span></div>
      </div>
      <div className="domain-totals">
        {Object.entries(domainMeta).map(([domain, meta]) => (
          <span key={domain} style={{ borderColor: meta.color }}><b>{meta.label}</b>{formatDuration(day.planSetId ? day.balance?.[domain] || 0 : managed.filter((item) => item.domain === domain).reduce((total, item) => total + item.duration_minutes, 0))}</span>
        ))}
      </div>
      {day.planSetId && managed.length > 0 && <p className="managed-summary">Your daily record: {managed.filter((item) => item.completion_status === "done").length}/{managed.length} done. The plan above is a saved snapshot.</p>}
    </section>
  );
}

/** Make Summary-agent day, week, and month reports visible with their evidence. */
function SummaryPanel({ reports, date, onOpen, compact = false }) {
  const [kind, setKind] = useState("day");
  const report = reports?.[kind];
  const domainRows = report ? Object.entries(report.domains || {}).filter(([, counts]) => counts.scheduled > 0) : [];
  const scheduled = domainRows.reduce((total, [, counts]) => total + counts.scheduled, 0);
  const done = domainRows.reduce((total, [, counts]) => total + counts.done, 0);
  const completion = scheduled ? Math.round((done / scheduled) * 100) : 0;
  return <section className={`summary-panel ${compact ? "compact" : ""}`} aria-label={`Summary Agent insights for ${date}`}>
    <div className="summary-heading"><div><small>SUMMARY AGENT</small><h2>What the records say</h2></div><div className="summary-switch" aria-label="Summary period">{["day", "week", "month"].map((period) => <button key={period} className={kind === period ? "active" : ""} onClick={() => setKind(period)} aria-pressed={kind === period}>{period}</button>)}</div></div>
    {report ? <>
      <div className="summary-scoreboard"><span><strong>{report.recordedDays}</strong><small>recorded days</small></span><span><strong>{completion}%</strong><small>completed</small></span><span><strong>{report.suggestions.length}</strong><small>next ideas</small></span></div>
      <div className="summary-body"><div className="summary-patterns"><small>BY AREA · {report.periodKey}</small>{domainRows.length ? domainRows.map(([domain, counts]) => <div key={domain}><b style={{ color: domainMeta[domain]?.color }}>{domainMeta[domain]?.label || domain}</b><span>{counts.done}/{counts.scheduled} done{counts.partial ? ` · ${counts.partial} partial` : ""}{counts.skipped ? ` · ${counts.skipped} skipped` : ""}</span></div>) : <p>No completed or skipped work has been reported for this period.</p>}</div><div className="summary-next"><small>NEXT BEST STEP</small>{report.suggestions.length ? report.suggestions.slice(0, 2).map((suggestion, index) => <p key={`${suggestion.domain}-${index}`}><b>{domainMeta[suggestion.domain]?.label || "Across areas"}</b>{suggestion.content}</p>) : <p>Keep recording outcomes; the agent will suggest changes when a pattern is supported.</p>}</div></div>
      {report.feedback.length > 0 && <details className="summary-memory"><summary>Preference memory ({report.feedback.length})</summary>{report.feedback.map((signal) => <p key={`${signal.domain}-${signal.taskTitle}`}>{signal.shortenRequests} request{signal.shortenRequests === 1 ? "" : "s"} to shorten {signal.taskTitle}{signal.protected && " · important to keep"}</p>)}</details>}
      <div className="summary-footer"><small>Based only on saved plans, outcomes, area records, goals, requests, and {report.knowledgeSourceCount} indexed source{report.knowledgeSourceCount === 1 ? "" : "s"}.</small>{onOpen && <button onClick={onOpen}>OPEN HISTORY →</button>}</div>
    </> : <p className="empty-copy">{reports ? "No report for this period." : "Start the local service to see saved Summary-agent reports."}</p>}
  </section>;
}

function SuggestionPoolPanel({ pool, onDiscard, onClearWeek }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState("day");
  const [domain, setDomain] = useState("all");
  const current = pool?.[kind];
  const items = (current?.items || []).filter((item) => domain === "all" || item.domain === domain);
  const notices = (current?.notices || []).filter((item) => domain === "all" || item.domain === domain);
  const activeCount = new Set(Object.values(pool || {}).flatMap((period) =>
    period.items.filter((item) => item.status === "active")
      .map((item) => `${item.domain}:${item.content}`))).size;
  return <section className="suggestion-pool" aria-label="Summary suggestion management">
    <div className="section-line"><small>SAVED SUMMARY ADVICE / {activeCount} ACTIVE IDEA{activeCount === 1 ? "" : "S"}</small>
      <button onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        {open ? "CLOSE ADVICE" : "MANAGE ADVICE →"}</button></div>
    {open && <>
      <div className="pool-filters" aria-label="Suggestion filters">
        {(["day", "week", "month"]).map((value) => <button key={value} onClick={() => setKind(value)}
          aria-pressed={kind === value}>{value.toUpperCase()}</button>)}
        <select aria-label="Suggestion area" value={domain} onChange={(event) => setDomain(event.target.value)}>
          <option value="all">All areas</option>{["learning", "life", "finance", "rest", "cross"].map((value) =>
            <option key={value} value={value}>{domainMeta[value]?.label || "Cross-domain"}</option>)}</select>
      </div>
      <small className="pool-period">{current?.periodKey || "No local report yet"}</small>
      {items.length ? items.map((item) => <div className="pool-item" key={item.id}>
        <span><b>{domainMeta[item.domain]?.label || "Cross-domain"} · {item.priority.toUpperCase()} · {item.status.toUpperCase()}</b><p>{item.content}</p></span>
        {item.status === "active" && <button onClick={() => onDiscard(item.id)}>DISCARD ACROSS PERIODS</button>}
      </div>) : <p className="empty-copy">No saved advice for this period and area.</p>}
      {notices.map((item, index) => <p className="pool-notice" key={`${item.domain}-${index}`} role="status">
        Previously discarded advice appeared again; it was not reactivated: {item.content}</p>)}
      {kind === "week" && domain !== "all" && (items.length > 0 || notices.length > 0) &&
        <button className="pool-clear" onClick={() => onClearWeek(current.periodKey, domain)}>
          CLEAR THIS WEEK + AREA PERMANENTLY</button>}
      <p className="empty-copy">Advice is guidance, not an applied plan. Discarding this idea stops
        its agent dispatch across periods; a matching later report shows a notice only.</p>
    </>}
  </section>;
}

/** Collect or edit one dated task without silently turning it into a plan. */
function DayItemForm({ date, goals, item, defaultDomain = "life", onSave, backendConnected, onCancel }) {
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
    protected: false, goalId: "", status: "planned",
  }), [date, item, defaultDomain]);

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
      <div className="section-line"><small>{item ? "EDIT DAILY RECORD" : `ADD TO ${date}`}</small><b>YOUR OWN DATA</b></div>
      <div className="daily-form-grid">
        <label>What needs doing?<input required maxLength="200" value={draft.title || ""} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="An appointment, errand, study block…" /></label>
        <label>Area<select value={draft.domain || "life"} onChange={(event) => setDraft({ ...draft, domain: event.target.value, goalId: "" })}>{Object.entries(domainMeta).map(([key, meta]) => <option key={key} value={key}>{meta.label}</option>)}</select></label>
        <div className="fixed-date"><small>DATE</small><strong>{date}</strong><span>Past days are read-only. Future commitments can be entered, but their outcomes wait.</span></div>
        <label>Time<input required type="time" value={draft.startTime || "09:00"} onChange={(event) => setDraft({ ...draft, startTime: event.target.value })} /></label>
        <label>Minutes<input required type="number" min="1" max="1440" value={draft.durationMinutes || 30} onChange={(event) => setDraft({ ...draft, durationMinutes: event.target.value })} /></label>
        <label>Kind<select value={draft.constraintKind || "flexible"} onChange={(event) => setDraft({ ...draft, constraintKind: event.target.value })}><option value="flexible">Flexible task</option><option value="fixed">Fixed commitment</option></select></label>
        <label>Repeat<select value={draft.repeatKind || "none"} onChange={(event) => setDraft({ ...draft, repeatKind: event.target.value })}><option value="none">One time</option><option value="daily">Every day</option><option value="weekly">Every week</option></select></label>
        <label>Related goal<select value={draft.goalId || ""} onChange={(event) => setDraft({ ...draft, goalId: event.target.value })}><option value="">None</option>{matchingGoals.map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select></label>
        <label className="detail-field">Details (optional)<input maxLength="1000" value={draft.detail || ""} onChange={(event) => setDraft({ ...draft, detail: event.target.value })} placeholder="Something you will recognize later" /></label>
        <label className="protected-field"><input type="checkbox" checked={Boolean(draft.protected)} onChange={(event) => setDraft({ ...draft, protected: event.target.checked })} /> Important to keep even if I later ask to shorten it</label>
      </div>
      <div className="form-actions"><button disabled={!backendConnected || !draft.title?.trim() || saving}>{saving ? "SAVING…" : item ? "SAVE CHANGES" : "ADD DAILY ITEM"}</button>{item && <button type="button" onClick={onCancel}>CANCEL</button>}{!backendConnected && <span>Start the local service to save your records.</span>}{error && <span role="alert">{error}</span>}</div>
    </form>
  );
}

/** Show user-authored daily records independently of proposed plan snapshots. */
function DayItemLedger({ day, onSave, onStatus, backendConnected, domain = null, readOnly = false, reportable = true }) {
  const [editing, setEditing] = useState(null);
  const [adding, setAdding] = useState(false);
  useEffect(() => { setEditing(null); setAdding(false); }, [day.date]);
  const items = domain ? day.dayItems.filter((item) => item.domain === domain || (domain === "life" && item.domain === "rest")) : day.dayItems;
  return (
    <section className="daily-ledger">
      <div className="section-line"><small>YOUR DAILY RECORDS / {day.date}</small>{readOnly ? <b>READ-ONLY HISTORY</b> : <button onClick={() => { setAdding((value) => !value); setEditing(null); }}>{adding ? "CLOSE FORM" : "+ ADD ITEM"}</button>}</div>
      {items.length ? items.map((item) => <div className="managed-entry" key={item.id}>
        <time>{item.start_time}</time><span><strong>{item.title}</strong><small>{domainMeta[item.domain].label} · {item.constraint_kind}{item.repeatKind !== "none" && ` · ${item.repeatKind}`}{Boolean(item.protected) && " · important to keep"}{item.goalId && ` · ${day.goals.find((goal) => goal.id === item.goalId)?.title || "goal"}`} · {item.originKind === "agent-origin" ? "AGENT-ORIGIN" : "PRESET BY YOU"}</small>{item.originKind === "agent-origin" && <small className="origin-evidence">{item.originDetail}</small>}</span>
        <label className="visually-hidden" htmlFor={`status-${item.id}`}>Progress for {item.title}</label>
        <select id={`status-${item.id}`} value={item.completion_status} disabled={!backendConnected || readOnly || !reportable} onChange={(event) => onStatus(item, event.target.value).catch(() => {})}><option value="planned">Planned</option><option value="done">Done</option><option value="partial">Partial</option><option value="skipped">Skipped</option></select>
        {!readOnly && <button onClick={() => { setEditing(item); setAdding(false); }}>EDIT</button>}
      </div>) : <p className="empty-copy">No daily items are recorded for this date.{readOnly ? " This past date has no editable items." : " Add a real task or commitment here."}</p>}
      {!readOnly && (adding || editing) && <DayItemForm date={day.date} goals={day.goals} item={editing} defaultDomain={domain || "life"} onSave={onSave} backendConnected={backendConnected} onCancel={() => setEditing(null)} />}
    </section>
  );
}

/** Manage durable goals and their completion from user-recorded daily items. */
function GoalsPage({ day, onSave, backendConnected, onToday }) {
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("learning");
  const [editing, setEditing] = useState(null);
  const [editedTitle, setEditedTitle] = useState("");
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
    <header className="workbench-header"><small>WELLSPENT / GOAL MANAGEMENT</small><span>{backendConnected ? "YOUR RECORDS · LOCAL" : "PREVIEW MODE · NOT SAVED"}</span></header>
    <div className="overview-hero"><div><small>LONGER HORIZON</small><h1>Goals</h1><p>Give each area a direction. Link dated items to a goal and report progress as it happens.</p></div><button onClick={onToday}>TODAY →</button></div>
    <div className="goals-layout"><section className="goals-ledger"><div className="section-line"><small>YOUR GOALS</small><b>{day.goals.length} RECORDED</b></div>
      {day.goals.length ? day.goals.map((goal) => <div className="goal-entry" key={goal.id}>
        <span className={`goal-area domain-${goal.domain}`}>{domainMeta[goal.domain].label.toUpperCase()}</span>
        <div><strong>{goal.title}</strong><small>{goal.doneCount}/{goal.itemCount} linked daily items done</small>{editing === goal.id && <form onSubmit={async (event) => { event.preventDefault(); try { setError(""); await onSave(goal.id, { title: editedTitle, status: goal.status }); setEditing(null); } catch (caught) { setError(caught.message); } }}><input required maxLength="200" value={editedTitle} onChange={(event) => setEditedTitle(event.target.value)} /><button>Save name</button></form>}</div>
        <select aria-label={`Status of ${goal.title}`} disabled={!backendConnected} value={goal.status} onChange={async (event) => { try { setError(""); await onSave(goal.id, { title: goal.title, status: event.target.value }); } catch (caught) { setError(caught.message); } }}><option value="active">Active</option><option value="paused">Paused</option><option value="completed">Completed</option></select>
        <button onClick={() => { setEditing(goal.id); setEditedTitle(goal.title); }}>EDIT</button>
      </div>) : <p className="empty-copy">No goals yet. Add your first learning, life, money, or rest goal.</p>}
    </section><form className="goal-capture" onSubmit={create}><small>SET A GOAL</small><label>What matters?<input required maxLength="200" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Build a steady exercise habit" /></label><label>Area<select value={domain} onChange={(event) => setDomain(event.target.value)}>{Object.entries(domainMeta).map(([key, meta]) => <option key={key} value={key}>{meta.label}</option>)}</select></label><button disabled={!backendConnected || !title.trim()}>ADD GOAL</button>{!backendConnected && <p>Start the local service to save goals.</p>}{error && <p role="alert">{error}</p>}</form></div>
  </main>;
}

function TodayPage({ day, reports, pool, onCalendar, onPlans, onGoals, onDomain, onChat, onSuggestion, onDiscardAdvice, onClearAdviceWeek, onItemSave, onItemStatus, backendConnected }) {
  const parts = dateParts(day.date);
  const activeGoals = day.goals.filter((goal) => goal.status === "active");
  return (
    <main className="workbench-page today-page">
      <header className="workbench-header"><small>WELLSPENT / DAILY MANAGEMENT</small><span>{backendConnected ? "LOCALLY SAVED · PRIVATE" : "PREVIEW MODE · NOT SAVED"}</span></header>
      {day.demoMode && <div className="demo-banner"><b>DEMO WORKSPACE</b><span>Sample goals, plans, and outcomes are isolated from your personal workspace.</span></div>}
      <div className="overview-hero">
        <div><small>{parts.monthYear.toUpperCase()} · YOUR LIFE LEDGER</small><h1>Today<span> / {parts.dayNumber}</span></h1><p>Manage the day you actually have: goals, commitments, progress, and a plan you choose.</p></div>
        <button onClick={onCalendar}>OPEN CALENDAR <ChevronRight aria-hidden="true" /></button>
      </div>
      {day.planSource === "deterministic-v1" && <div className="legacy-warning" role="note"><strong>EXAMPLE PLAN, NOT YOUR PERSONAL DATA</strong><span>This earlier prototype day contains sample commitments and notes. Your own goals and daily items below remain separate; no sample is counted as your history.</span></div>}
      {!day.goals.length && !day.dayItems.length && !day.planSetId && <div className="welcome-management"><Target aria-hidden="true" /><div><strong>Start with your real life.</strong><p>Set one goal and add a dated task or fixed commitment. Wellspent will not invent your calendar.</p></div><button onClick={onGoals}>SET YOUR FIRST GOAL →</button></div>}
      <div className="management-strip" aria-label="Today's execution overview"><button onClick={onPlans}><small>TODAY'S PLAN</small><strong>{day.confirmedVariantId ? "LIVE" : day.planSetId ? "DRAFT" : "NONE"}</strong><span>{day.planSetId ? "Review schedule →" : "Build from your items →"}</span></button><button onClick={() => onChat("ask")}><small>LOCAL AI</small><strong>{day.model?.running ? "READY" : "START"}</strong><span>Ask or adjust today →</span></button><button onClick={onGoals}><small>ACTIVE GOALS</small><strong>{activeGoals.length}</strong><span>Review direction →</span></button></div>
      <div className="management-columns"><DayItemLedger day={day} onSave={onItemSave} onStatus={onItemStatus} backendConnected={backendConnected} /><aside className="management-side"><div className="assistant-card"><span className={`model-dot ${day.model?.running ? "running" : ""}`} /><strong>{day.model?.running ? "Local AI is ready" : "Local AI is available"}</strong><p>{day.model?.running ? "Qwen is connected on this Mac. Ask a question or request a plan adjustment." : "The model starts locally when you send your first message."}</p><button onClick={() => onChat("ask")}>ASK WELLSPENT →</button></div><div className="section-line"><small>ACTIVE GOALS / {activeGoals.length}</small><button onClick={onGoals}>MANAGE →</button></div>{activeGoals.slice(0, 3).map((goal) => <div className="goal-mini" key={goal.id}><b>{domainMeta[goal.domain].label}</b><strong>{goal.title}</strong><small>{goal.doneCount}/{goal.itemCount} linked items done</small></div>)}</aside></div>
      <div className="area-shortcuts"><small>MANAGE AN AREA</small>{["learning", "life", "finance"].map((domain) => <button key={domain} onClick={() => onDomain(domain)}>{domainMeta[domain].label} <ChevronRight aria-hidden="true" /></button>)}</div>
      <Suggestion suggestion={day.suggestion} onDecision={onSuggestion} />
    </main>
  );
}

function CalendarPage({ month, days, day, reports, today, onMonth, onSelect, onToday, onPlans, onDomain, onUpdate, onItemSave, onItemStatus, onBuild, backendConnected }) {
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
      <header className="workbench-header"><small>WELLSPENT / CALENDAR</small><span>{backendConnected ? "RECORDED DAYS · NO AUTO-FILLED HISTORY" : "PREVIEW MODE · NOT SAVED"}</span></header>
      <div className="calendar-title"><div><small>HISTORY + MANAGEMENT</small><h1>{monthTitle(month)}</h1></div><div className="month-actions"><button aria-label="Previous month" onClick={() => onMonth(shiftMonth(month, -1))}><ChevronLeft aria-hidden="true" /></button><button onClick={onToday}>TODAY</button><button aria-label="Next month" onClick={() => onMonth(shiftMonth(month, 1))}><ChevronRight aria-hidden="true" /></button><label>JUMP TO DATE<input type="date" value={day.date} onChange={(event) => event.target.value && onSelect(event.target.value)} /></label></div></div>
      <div className="month-summary" aria-label={`Summary for ${monthTitle(month)}`}><small>MONTH SUMMARY <b>RECORDED HISTORY ONLY</b></small><span><b>{recordedCount}</b> days with records</span><span><b>{confirmedCount}</b> confirmed plans</span><span><b>{doneCount}/{entryCount}</b> done / scheduled</span><span><b>{managedCount}</b> user-owned items</span></div>
      {recentPlans.length > 0 && <div className="past-plan-strip"><small>PAST CONFIRMED PLANS</small>{recentPlans.map((record) => <button key={record.date} onClick={() => onSelect(record.date)}><b>{dateParts(record.date).day} {dateParts(record.date).dayNumber}</b><span>{record.variantName || "Saved plan"} · {record.doneCount}/{record.entryCount} done</span></button>)}</div>}
      <div className="calendar-layout">
        <section className="month-sheet" aria-label={`${monthTitle(month)} calendar`}>
          <div className="weekday-head">{["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"].map((label) => <span key={label}>{label}</span>)}</div>
          <div className="month-grid">{dates.map((date) => {
            const record = records.get(date);
            return <button key={date} className={`month-day ${date.slice(0, 7) !== month ? "outside" : ""} ${date === day.date ? "selected" : ""} ${date === today ? "is-today" : ""}`} onClick={() => onSelect(date)} aria-label={`${date}${record ? `, ${record.confirmed ? "confirmed plan" : record.planSource ? "draft plan" : "daily records"}, ${record.doneCount} of ${record.entryCount} done` : ", no recorded history"}`} aria-current={date === day.date ? "date" : undefined}>
              <b>{Number(date.slice(-2))}</b>{record && <span className={record.confirmed ? "confirmed-mark" : "draft-mark"}>{record.confirmed ? "PLAN" : record.planSource ? "DRAFT" : "RECORDED"}<i>{record.doneCount}/{record.entryCount}</i></span>}
            </button>;
          })}</div>
          <p className="month-legend"><span /> Confirmed plan <i /> Draft or personal record · Empty dates have no stored history</p>
        </section>
        <aside className="calendar-detail">
          <div className="section-line"><small>SELECTED DAY</small><b>{day.date}</b></div>
          <h2>{dateParts(day.date).day} / {dateParts(day.date).dayNumber}</h2>
          <DaySummary day={day} />
          {day.planSource === "deterministic-v1" && <p className="legacy-warning">This older saved plan is a prototype example, not a user-authored schedule.</p>}
          {day.planSetId ? <>
            <p className="calendar-plan-note">{day.date !== today ? "Saved plans outside today are read-only snapshots in the calendar." : day.confirmedVariantId ? "This is the confirmed plan shared with the area ledgers." : "This is an unconfirmed draft. Reporting opens after confirmation."}</p>
            <button className="text-link" onClick={onPlans}>{day.date !== today ? "VIEW SAVED PLAN" : day.confirmedVariantId ? "REVIEW PLAN" : "CHOOSE A PLAN"} →</button>
            <div className="calendar-area-links">{["learning", "life", "finance"].map((domain) => <button key={domain} onClick={() => onDomain(domain)}>{domainMeta[domain].label} →</button>)}</div>
          </> : <><p className="empty-copy">{day.dayItems.length ? "Your dated records are shown below. No plan snapshot was saved for this date." : day.date < today ? "No plan was recorded for this past date. It cannot be created retroactively." : day.date > today ? "No plan yet. Record future commitments below; proposing and confirming wait until that day." : "No stored history yet. Add a real item today; browsing alone does not invent a plan."}</p>{day.date === today && day.dayItems.length > 0 && <button className="text-link" onClick={onBuild}>BUILD PLAN FROM THESE ITEMS →</button>}</>}
        </aside>
      </div>
      <SummaryPanel reports={reports} date={day.date} />
      <DayItemLedger day={day} onSave={onItemSave} onStatus={onItemStatus} backendConnected={backendConnected} readOnly={day.date < today} reportable={day.date === today} />
      {day.entries.length > 0 && <section className="calendar-schedule"><div className="section-line"><small>PLAN SNAPSHOT ON {day.date}</small><b>{day.date !== today ? "READ-ONLY HISTORY" : day.confirmedVariantId ? "CURRENT PLAN" : "DRAFT PREVIEW"}</b></div><Schedule entries={day.entries} onUpdate={onUpdate} canReport={day.date === today && Boolean(day.confirmedVariantId)} title="SCHEDULED ITEMS" /></section>}
    </main>
  );
}

function Suggestion({ suggestion, onDecision }) {
  if (!suggestion) return null;
  if (suggestion.decision) {
    return (
      <div className="suggestion resolved">
        <Paperclip className="paperclip" aria-hidden="true" />
        <div><small>SUGGESTION FILED</small><strong>{suggestion?.decision === "kept" ? "Added to your notes." : "No problem — it’s out of the way."}</strong></div>
      </div>
    );
  }
  return (
    <aside className="suggestion">
      <Paperclip className="paperclip" aria-hidden="true" />
      <div className="suggestion-copy">
        <small>SUGGESTION</small>
        <strong>{suggestion.title}</strong>
        <p>{suggestion.detail}</p>
      </div>
      <button className="keep" onClick={() => onDecision("kept")}>Keep</button>
      <span className="button-divider" />
      <button className="dismiss" onClick={() => onDecision("dismissed")}>Dismiss</button>
    </aside>
  );
}

function BalanceRow({ domain, minutes }) {
  const meta = domainMeta[domain];
  return (
    <div className="balance-row">
      <strong style={{ color: meta.color }}>{meta.label.toUpperCase()}</strong>
      <span>{formatDuration(minutes)}</span><i>—</i><small>{meta.statement}</small>
    </div>
  );
}

/** Keep comparison, schedule, rationale, and confirmation on one management surface. */
function PlanDesk({ day, reports, readOnly, onVariant, onConfirm, onReplace, onCancelReplace, replacing, onChat, backendConnected }) {
  const selected = day.variants.find((variant) => variant.id === day.selectedVariantId) || day.variants[0];
  const confirmed = day.confirmedVariantId === day.selectedVariantId;
  const confirmedName = day.variants.find((variant) => variant.id === day.confirmedVariantId)?.name;
  return (
    <main className="workbench-page plan-desk">
      <header className="workbench-header"><small>WELLSPENT / PLAN MANAGEMENT</small><span>{backendConnected ? "LOCAL PLAN SNAPSHOT" : "PREVIEW MODE · NOT SAVED"}</span></header>
      <div className="plan-desk-heading"><div><small>{day.date} · {readOnly ? "READ-ONLY HISTORY" : confirmed ? "CURRENT PLAN" : "ALTERNATIVE PREVIEW"}</small><h1>{readOnly ? "A day preserved." : "Shape this day."}</h1><p>{readOnly ? "This saved past plan and its reported outcome cannot be changed." : "Compare only what has been saved for this date. Review the schedule and the decision together."}</p></div><span className={`model-dot ${day.model?.running ? "running" : ""}`} title={day.model?.label} /></div>
      {day.planSource === "deterministic-v1" && <div className="legacy-warning"><strong>PROTOTYPE EXAMPLE</strong><span>These older sample appointments and energy notes were not supplied by you. Add your own daily items to manage real life; future plans start from those records.</span></div>}
      <div className="plan-choice"><div className="section-line"><small>{readOnly ? "SAVED PLAN / PAST DATE" : "PLAN ALTERNATIVES / SAME DATE"}</small><b>{confirmedName ? `${confirmedName.toUpperCase()} IS CONFIRMED` : "NOT YET CONFIRMED"}</b></div>{!readOnly && <div className="variant-tabs" aria-label="Plan alternatives">{day.variants.map((variant) => <button className={variant.id === day.selectedVariantId ? "active" : ""} key={variant.id} onClick={() => onVariant(variant.id)} aria-pressed={variant.id === day.selectedVariantId}>{variant.name}{variant.id === day.confirmedVariantId && <small>✓ CURRENT</small>}</button>)}</div>}<p>{selected.rationale}</p></div>
      <AgentTrail route={day.planRoute} />
      <div className="plan-overview"><div><small>ALLOCATION</small>{Object.entries(day.balance).map(([domain, minutes]) => <BalanceRow domain={domain} minutes={minutes} key={domain} />)}</div><div><small>FIXED COMMITMENTS</small>{day.hardConstraints.length ? day.hardConstraints.map((constraint) => <p key={constraint}>{constraint}</p>) : <p>No fixed commitments were recorded.</p>}</div><div><small>PLANNER NOTES</small>{day.plannerNotes.map((note) => <p key={note}>{note}</p>)}</div></div>
      <div className="section-line"><small>SCHEDULE / {selected.name.toUpperCase()}</small><b>{confirmed ? "CURRENT" : "PREVIEW ONLY"}</b></div><Schedule entries={day.entries} title="TIMED ITEMS" />
      {readOnly ? <SummaryPanel reports={reports} date={day.date} /> : <><div className="plan-decision"><div><small>DECISION FILE</small><strong>{confirmed ? "This plan is in motion." : confirmedName ? `Currently confirmed: ${confirmedName}` : "Nothing changes until you confirm."}</strong><p>Completion is reported explicitly. A different confirmed plan requires a named replacement.</p></div><div><button className="confirm-button" onClick={onConfirm} disabled={confirmed || replacing || !backendConnected}>{confirmed ? "CURRENT PLAN CONFIRMED" : confirmedName ? "REVIEW REPLACEMENT" : "CONFIRM THIS PLAN"}</button><button onClick={() => onChat("adjust")}>MARK UP WITH AGENTS</button></div></div>{replacing && <div className="replace-review" role="group" aria-label="Approve plan replacement"><p>Replace the confirmed {confirmedName} plan with {selected.name} for {day.date}? Calendar and area ledgers will switch. Reports on the previous alternative remain attached to it.</p><button onClick={onReplace}>YES, REPLACE PLAN</button><button onClick={onCancelReplace}>KEEP {confirmedName?.toUpperCase()}</button></div>}</>}
    </main>
  );
}

function EmptyPlanDesk({ day, today, onBuild, onSave, onStatus, backendConnected }) {
  const past = day.date < today;
  return <main className="workbench-page plan-desk">
    <header className="workbench-header"><small>WELLSPENT / PLAN MANAGEMENT</small></header>
    <div className="overview-hero"><div><small>{day.date} · YOUR RECORDS FIRST</small><h1>No plan yet</h1><p>{past ? "No plan was saved for this past date. Its records are read-only." : day.date > today ? "Enter future commitments now. Their plan and outcomes wait until that day arrives." : day.dayItems.length ? "Your timed daily items can become agent-proposed alternatives. Build them explicitly, then review before confirming." : "Add actual tasks and commitments first. Wellspent never generates an invented sample day for a new user."}</p></div>{day.date === today && <button disabled={!backendConnected} onClick={onBuild}>PROPOSE DAY PLANS →</button>}</div>
    <DayItemLedger day={day} onSave={onSave} onStatus={onStatus} backendConnected={backendConnected} readOnly={past} reportable={day.date === today} />
  </main>;
}

function ConversationDrawer({ open, onClose, day, mode, setMode, onSent, backendConnected }) {
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
        body: JSON.stringify({ date: day.date, message: trimmed, mode, selectedVariantId: day.selectedVariantId }),
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
      <button className="conversation-scrim" onClick={onClose} aria-label="Close conversation" tabIndex={open ? 0 : -1} />
      <aside className="conversation-drawer" role="dialog" aria-modal="true" aria-label="Talk with Wellspent">
        <header>
          <div><small>LOCAL MULTI-AGENT WORKBENCH</small><h2>Talk it through.</h2></div>
          <button onClick={onClose} aria-label="Close"><Icon name="close" /></button>
        </header>
        <div className="model-card">
          <span className={`model-dot ${day.model?.running ? "running" : ""}`} />
          <div><strong>5 agents · local RAG + Qwen synthesis</strong><small>{day.model?.label || "Local model"} · {day.rag?.vectorStore?.sourceCount || 0} indexed {(day.rag?.vectorStore?.sourceCount || 0) === 1 ? "source" : "sources"}</small></div>
          <b>PRIVATE</b>
        </div>
        <div className="mode-switcher">
          {Object.entries(modeCopy).map(([id, [label]]) => (
            <button key={id} className={mode === id ? "active" : ""} onClick={() => setMode(id)}>{label}</button>
          ))}
        </div>
        <p className="mode-help">{modeCopy[mode][1]}</p>
        <div className="message-list" ref={listRef} aria-live="polite">
          {messages.length === 0 && (
            <div className="opening-message">
              <Icon name="spark" />
              <p><strong>Your day has room to breathe.</strong> The Orchestrator consults Learning, Life, Finance, and Summary as needed—then shows you the route.</p>
            </div>
          )}
          {messages.map((item) => (
            <div className={`message ${item.role}`} key={item.id}>
              <small>{item.role === "user" ? "YOU" : "WELLSPENT"}</small><p>{item.content}</p>
              {item.role === "assistant" && <RetrievalTrail retrieval={item.retrieval} />}
              {item.role === "assistant" && <AgentTrail route={item.agentRoute} />}
            </div>
          ))}
          {sending && <div className="message assistant thinking"><small>ORCHESTRATOR</small><p>Consulting the relevant agents locally<span>…</span></p></div>}
          {proposal && (
            <div className="proposal-card">
              <small>PROPOSED CHANGE</small><strong>{proposal.actionType === "shorten_future_item" ? "Shorten future commitment" : proposal.payload.reviewedFromVariantName ? `Replace ${proposal.payload.reviewedFromVariantName} with ${proposal.payload.variantName}` : `Choose ${proposal.payload.variantName}`}</strong><p>{proposal.explanation}</p>
              <div><button onClick={() => decide("confirmed")}>{proposal.payload.reviewedFromVariantName ? "Approve named replacement" : "Confirm change"}</button><button onClick={() => decide("dismissed")}>Keep current</button></div>
            </div>
          )}
        </div>
        <form className="composer" onSubmit={send}>
          <button type="button" className={`mic-button ${voiceState === "recording" ? "recording" : ""}`} onClick={toggleVoice} disabled={!backendConnected || day.voice?.state !== "available" || sending || voiceState === "starting" || voiceState === "transcribing"} aria-label={voiceState === "recording" ? "Stop push-to-talk and transcribe locally" : "Start push-to-talk recording"} aria-pressed={voiceState === "recording"} title={day.voice?.state === "available" ? "Push to talk; press again to transcribe on this Mac" : day.voice?.label || "Local Whisper speech runtime needs setup"}><Icon name="mic" /></button>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={mode === "adjust" ? "Make the afternoon lighter…" : "Ask about your day…"}
            rows="2"
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send(event);
              }
            }}
          />
          <button className="send-button" type="submit" disabled={!message.trim() || sending} aria-label="Send message"><Icon name="send" /></button>
        </form>
        <p className="voice-status" role="status">{voiceError || (voiceState === "recording" ? "Recording on this Mac · press the microphone again to finish" : voiceState === "starting" ? "Requesting microphone access…" : voiceState === "transcribing" ? "Transcribing locally…" : voiceState === "recognized" ? "Text added locally · review it before sending" : day.voice?.state === "available" ? "Voice ready · press the microphone to talk" : day.voice?.label || "Local speech runtime needs setup")}</p>
        <p className="composer-footnote">A proposal is not an action. You stay in control.</p>
      </aside>
    </div>
  );
}

function KnowledgeCapture({ backendConnected, onSaved }) {
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
      <small>ADD PRIVATE KNOWLEDGE</small>
      <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Recovery notes" /></label>
      <label>Text<textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Paste a note Wellspent may retrieve later…" rows="5" /></label>
      {error && <p role="alert">{error}</p>}
      <button disabled={!backendConnected || !title.trim() || !text.trim() || saving}>{saving ? "Indexing locally…" : "Chunk + index note"}</button>
    </form>
  );
}

function KnowledgeTopic({ backendConnected, onSaved }) {
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
    <small>FIND A TOPIC</small>
    <label>Topic<input value={topic} maxLength={200} onChange={(event) => setTopic(event.target.value)} placeholder="A topic you want to learn" /></label>
    <label className="knowledge-web-choice"><input type="checkbox" checked={explicitWeb} onChange={(event) => setExplicitWeb(event.target.checked)} /> Fetch from the public web even when local notes match</label>
    <p className="empty-copy">Your entered topic alone goes to Wikipedia if local knowledge has no semantic match, or when you check the box. Your notes and calendar never go with it.</p>
    {error && <p role="alert">{error}</p>}
    {result && <p role="status">{result.publicFetch === "awaiting_import_choice" ? "Public introduction fetched. Choose how to organize it before indexing; your local library is unchanged." : result.publicFetch === "imported" ? "Your chosen organization was indexed locally." : result.publicFetch === "needs_general_topic" ? "This looks personal. Try a general topic without 'my', contact details, or identifying numbers; no public search was made." : result.retrieval?.status === "ready" ? "Found in your local knowledge" : "Local search unavailable; nothing was fetched"}{result.source?.sourceUrl && <> · <a href={result.source.sourceUrl} target="_blank" rel="noopener noreferrer">Wikipedia source and attribution ↗</a></>}</p>}
    <button disabled={!backendConnected || !topic.trim() || searching}>{searching ? "Searching…" : explicitWeb ? "Check local + fetch public" : "Find local match"}</button>
    {pending.some((item) => item.acquisitionId !== options?.acquisitionId) && <div className="pending-topics"><small>PENDING PUBLIC IMPORTS</small>{pending.filter((item) => item.acquisitionId !== options?.acquisitionId).map((item) =>
      <button type="button" key={item.acquisitionId} onClick={() => {
        setResult({ publicFetch: "awaiting_import_choice", importOptions: item });
        setSelectedPlanId(item.selectedPlanId || item.plans[0]?.id || "");
        setTopic(item.topic);
      }}>{item.topic} · review choices →</button>)}</div>}
    {options && result.publicFetch === "awaiting_import_choice" && <div className="import-choices">
      <small>PUBLIC SOURCE / <a href={options.sourceUrl} target="_blank" rel="noopener noreferrer">{options.sourceTitle} ↗</a> · {options.sourceLicense}</small>
      <p>Filter order: credibility, then timeliness, then format. Last edit: {options.filter.timeliness}. This is one attributed encyclopedia introduction, not a full source comparison.</p>
      <p>The schemes below describe organization labels. Automatic paragraph-level classification is not yet verified; the source text will be indexed without invented category claims.</p>
      {options.plans.map((plan) => <label className="import-choice" key={plan.id}>
        <input type="radio" name={`import-${options.acquisitionId}`} checked={selectedPlanId === plan.id}
          onChange={() => setSelectedPlanId(plan.id)} />
        <span><b>{plan.name}</b><small>{plan.labels.join(" / ")}</small></span>
      </label>)}
      <button type="button" onClick={confirmImport} disabled={!selectedPlanId || importing}>
        {importing ? "INDEXING LOCALLY…" : "CONFIRM IMPORT CHOICE"}</button>
    </div>}
  </form>;
}

function LocalFileImport({ backendConnected, onSaved }) {
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
          "X-Wellspent-Filename": filename }, body: file,
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
    <small>IMPORT A LOCAL FILE</small>
    <label>Choose Markdown, PDF, or Word (.docx)<input type="file" accept=".md,.markdown,.pdf,.docx" onChange={choose} /></label>
    <p className="empty-copy">Text is extracted and indexed on this Mac. No file or private note is sent to the public web. Scanned PDFs need text recognition first.</p>
    {error && <p role="alert">{error}</p>}{saved && <p role="status">{saved}</p>}
    <button disabled={!backendConnected || !file || saving}>{saving ? "Extracting and indexing locally…" : "Import selected file"}</button>
  </form>;
}

function DomainPage({ section, day, today, onToday, onCalendar, onGoals, onChat, onUpdate, onItemSave, onItemStatus, backendConnected, onKnowledgeSaved, onAreaSaved }) {
  const [areaView, setAreaView] = useState("state");
  useEffect(() => setAreaView("state"), [section]);
  const sourceCount = day.rag?.vectorStore?.sourceCount || 0;
  const copy = {
    learning: ["Learning", "Manage subjects, explicit learning sessions, goals, and dated work."],
    life: ["Life + rest", "Manage daily state, habits, timed events, and recovery."],
    finance: ["Money", "Manage manual transactions, a balance, budgets, and dated work."],
    library: ["Library", "Index private notes or enter a topic for local-first research. Library sources are not calendar events."],
  };
  const [title, description] = copy[section];
  const isArea = ["learning", "life", "finance"].includes(section);
  const scheduledEntries = isArea ? day.entries.filter((entry) => entry.domain === section || (section === "life" && entry.domain === "rest")) : [];
  const relatedGoals = day.goals.filter((goal) => goal.domain === section || (section === "life" && goal.domain === "rest"));
  return (
    <main className={`workbench-page area-page area-${section}`}>
      <header className="workbench-header"><small>WELLSPENT / {section.toUpperCase()}</small><span>{backendConnected ? "USER-OWNED RECORDS · LOCAL" : "PREVIEW MODE · NOT SAVED"}</span></header>
      <div className="overview-hero"><div><small>MANAGE AN AREA / {day.date}</small><h1>{title}</h1><p>{description}</p></div><button onClick={onCalendar}>CALENDAR →</button></div>
      {isArea ? <><div className="area-view-switch" aria-label="Area management views"><button className={areaView === "state" ? "active" : ""} onClick={() => setAreaView("state")}>AREA STATE</button><button className={areaView === "ledger" ? "active" : ""} onClick={() => setAreaView("ledger")}>DAY LEDGER + PLAN</button></div>{areaView === "state" ? <DomainRecordsBoard key={`${section}-${day.date}`} domain={section} date={day.date} today={today} backendConnected={backendConnected} onSaved={onAreaSaved} /> : <><div className="area-goals"><div className="section-line"><small>GOALS IN THIS AREA</small><button onClick={onGoals}>MANAGE GOALS →</button></div>{relatedGoals.length ? relatedGoals.map((goal) => <span key={goal.id}><strong>{goal.title}</strong><small>{goal.status} · {goal.doneCount}/{goal.itemCount} linked items done</small></span>) : <p className="empty-copy">No goals recorded in this area.</p>}</div><DayItemLedger day={day} domain={section} onSave={onItemSave} onStatus={onItemStatus} backendConnected={backendConnected} readOnly={day.date < today} reportable={day.date === today} />{scheduledEntries.length > 0 && <div className="area-plan"><div className="section-line"><small>{day.date} / {day.date !== today ? "READ-ONLY PLAN" : day.confirmedVariantId ? "CONFIRMED PLAN" : "DRAFT PLAN"}</small><button onClick={onCalendar}>VIEW WHOLE DAY →</button></div><Schedule entries={scheduledEntries} onUpdate={onUpdate} canReport={day.date === today && Boolean(day.confirmedVariantId)} title="PLAN SNAPSHOT" /></div>}</>}</> : <div className="library-management"><div><strong>{sourceCount} indexed source{sourceCount === 1 ? "" : "s"}</strong><p>Chunked notes are retrieved through sqlite-vec and a separate local embedding model. Only saved sources can support an answer.</p><button onClick={() => onChat("ask")}>TALK ABOUT YOUR SOURCES →</button></div><KnowledgeTopic backendConnected={backendConnected} onSaved={onKnowledgeSaved} /><LocalFileImport backendConnected={backendConnected} onSaved={onKnowledgeSaved} /><KnowledgeCapture backendConnected={backendConnected} onSaved={onKnowledgeSaved} /></div>}
      <button className="back-to-today" onClick={onToday}>← TODAY</button>
    </main>
  );
}

export function App() {
  const today = useMemo(localToday, []);
  const previewTodayRef = useRef(emptyDay(today));
  const [day, setDay] = useState(() => emptyDay(today));
  const [planPreview, setPlanPreview] = useState(() => emptyDay(today));
  const [month, setMonth] = useState(today.slice(0, 7));
  const [calendarDays, setCalendarDays] = useState([]);
  const [reports, setReports] = useState(null);
  const [pool, setPool] = useState(null);
  const summaryRequestRef = useRef(0);
  const [backendConnected, setBackendConnected] = useState(false);
  const [activeTab, setActiveTab] = useState("today");
  const [replacing, setReplacing] = useState(false);
  const [conversationOpen, setConversationOpen] = useState(false);
  const [conversationMode, setConversationMode] = useState("ask");
  const [notice, setNotice] = useState("");

  function showNotice(message) {
    setNotice(message);
    window.clearTimeout(showNotice.timer);
    showNotice.timer = window.setTimeout(() => setNotice(""), 2800);
  }

  async function loadSummaries(value) {
    const request = ++summaryRequestRef.current;
    try {
      const result = await getSummaries(value);
      if (request === summaryRequestRef.current) {
        setReports(result.reports);
        setPool(result.pool);
      }
    } catch {
      if (request === summaryRequestRef.current) { setReports(null); setPool(null); }
    }
  }

  async function loadDay(date, createIfMissing = false) {
    try {
      const result = await getDay(date, null, createIfMissing);
      setDay(result);
      setBackendConnected(true);
      loadSummaries(date);
      if (date === today) previewTodayRef.current = result;
      return result;
    } catch {
      setBackendConnected(false);
      setReports(null);
      setPool(null);
      const fallback = date === today ? previewTodayRef.current : emptyDay(date);
      setDay(fallback);
      return fallback;
    }
  }

  async function loadCalendar(value) {
    try {
      const result = await getCalendar(value);
      setCalendarDays(result.days);
    } catch {
      const preview = previewTodayRef.current;
      setCalendarDays(value === today.slice(0, 7) && (preview.planSetId || preview.dayItems.length) ? [previewCalendarDay(preview)] : []);
    }
  }

  useEffect(() => {
    loadDay(today, false).then((result) => setPlanPreview(result));
    loadCalendar(today.slice(0, 7));
  }, []);

  async function navigate(section) {
    setReplacing(false);
    if (section === "today") {
      setActiveTab("today");
      setMonth(today.slice(0, 7));
      if (backendConnected) await loadDay(today, false);
      else setDay(previewTodayRef.current);
      return;
    }
    if (section === "plans") setPlanPreview(day);
    setActiveTab(section);
  }

  function openPlans() {
    setPlanPreview(day);
    setReplacing(false);
    setActiveTab("plans");
  }

  async function chooseDate(date) {
    setReplacing(false);
    setActiveTab("calendar");
    if (date.slice(0, 7) !== month) {
      setMonth(date.slice(0, 7));
      loadCalendar(date.slice(0, 7));
    }
    await loadDay(date, false);
  }

  function chooseMonth(value) {
    setMonth(value);
    loadCalendar(value);
    loadDay(`${value}-01`, false);
  }

  async function selectVariant(variantId) {
    setReplacing(false);
    if (backendConnected) {
      try {
        setPlanPreview(await getDay(day.date, variantId, false));
      } catch (error) {
        showNotice(error.message);
      }
      return;
    }
    showNotice("Start the local service to retrieve a saved alternative.");
  }

  async function confirm() {
    if (planPreview.confirmedVariantId === planPreview.selectedVariantId) {
      showNotice("This plan is already confirmed.");
      return;
    }
    if (planPreview.confirmedVariantId) {
      setReplacing(true);
      return;
    }
    await applyConfirmation(false);
  }

  async function applyConfirmation(replaceExisting) {
    if (!backendConnected) {
      showNotice("Start the local service to save a plan confirmation.");
      return;
    }
    if (backendConnected) {
      try {
        await api("/api/plan/confirm", { method: "POST", body: JSON.stringify({ date: planPreview.date, variantId: planPreview.selectedVariantId, replaceExisting }) });
        const current = await loadDay(planPreview.date, false);
        setPlanPreview(current);
        await loadCalendar(month);
      } catch (error) {
        showNotice(error.message);
        return;
      }
    }
    setReplacing(false);
    showNotice(replaceExisting ? "Confirmed plan replaced for this date." : "Day confirmed. Calendar and area ledgers are updated.");
  }

  async function updateEntry(entryId, status) {
    if (!backendConnected) {
      showNotice("Start the local service to report progress.");
      return;
    }
    if (backendConnected) {
      try {
        await api(`/api/entries/${entryId}`, { method: "PATCH", body: JSON.stringify({ status }) });
      } catch (error) {
        showNotice(error.message);
        return;
      }
    }
    await loadDay(day.date, false);
    await loadCalendar(month);
    showNotice(`Marked ${status}.`);
  }

  async function decideSuggestion(decision) {
    if (backendConnected) {
      try {
        await api(`/api/suggestions/${day.suggestion.id}`, { method: "POST", body: JSON.stringify({ decision }) });
      } catch (error) {
        showNotice(error.message);
        return;
      }
    }
    const updated = { ...day, suggestion: { ...day.suggestion, decision } };
    setDay(updated);
    if (!backendConnected && day.date === today) previewTodayRef.current = updated;
  }

  async function discardAdvice(suggestionId) {
    try {
      const outcome = await api(`/api/suggestion-pool/${suggestionId}/discard`, { method: "POST" });
      await loadSummaries(day.date);
      showNotice(`Advice discarded across ${outcome.affectedPeriods} period${outcome.affectedPeriods === 1 ? "" : "s"}.`);
    } catch (error) { showNotice(error.message); }
  }

  async function clearAdviceWeek(week, domain) {
    const expected = `CLEAR ${week} ${domain.toUpperCase()}`;
    const typed = window.prompt(`This permanently deletes saved advice and repeat notices for ${week} / ${domain}. It cannot be undone. Type ${expected} to confirm:`);
    if (typed !== expected) return;
    try {
      const outcome = await api("/api/suggestion-pool/clear-week", {
        method: "POST", body: JSON.stringify({ week, domain, confirmation: typed }),
      });
      await loadSummaries(day.date);
      showNotice(`Permanently cleared ${outcome.deletedAdvice} weekly advice item${outcome.deletedAdvice === 1 ? "" : "s"}.`);
    } catch (error) { showNotice(error.message); }
  }

  async function saveGoal(goalId, payload) {
    if (!backendConnected) return;
    try {
      await api(goalId ? `/api/goals/${goalId}` : "/api/goals", {
        method: goalId ? "PUT" : "POST", body: JSON.stringify(payload),
      });
      await loadDay(day.date, false);
      showNotice(goalId ? "Goal updated." : "Goal added to your ledger.");
    } catch (error) {
      showNotice(error.message);
      throw error;
    }
  }

  async function saveItem(payload, itemId = null) {
    if (!backendConnected) return;
    try {
      await api(itemId ? `/api/daily-items/${itemId}` : "/api/daily-items", {
        method: itemId ? "PUT" : "POST", body: JSON.stringify(payload),
      });
      await loadCalendar(month);
      if (payload.date !== day.date) {
        await chooseDate(payload.date);
      } else {
        await loadDay(day.date, false);
      }
      showNotice(itemId ? "Daily item updated." : "Daily item recorded. It now appears in Calendar and its area.");
    } catch (error) {
      showNotice(error.message);
      throw error;
    }
  }

  async function updateItemStatus(item, status) {
    await saveItem({
      date: item.date, title: item.title, detail: item.detail, domain: item.domain,
      startTime: item.start_time, durationMinutes: item.duration_minutes,
      constraintKind: item.constraint_kind, repeatKind: item.repeatKind,
      protected: Boolean(item.protected), goalId: item.goalId, status,
    }, item.id);
  }

  async function buildPlan() {
    if (!backendConnected) {
      showNotice("Start the local service to build a saved plan.");
      return;
    }
    try {
      await api("/api/plan/generate", { method: "POST", body: JSON.stringify({ date: day.date }) });
      const current = await loadDay(day.date, false);
      setPlanPreview(current);
      await loadCalendar(month);
      setActiveTab("plans");
      showNotice("Built a plan from your dated items. Review it before confirming.");
    } catch (error) {
      showNotice(error.message);
    }
  }

  function openConversation(mode = "ask") {
    setConversationMode(mode);
    setConversationOpen(true);
  }

  async function handleConversationUpdate(model, variantId, changedDate) {
    if (variantId) {
      const current = await loadDay(day.date, false);
      setPlanPreview(current);
      await loadCalendar(month);
      showNotice("The proposed plan is now confirmed and shown in Calendar.");
      return;
    }
    if (changedDate) {
      await loadDay(changedDate, false);
      await loadCalendar(changedDate.slice(0, 7));
      showNotice("Future commitment updated; its origin remains visible.");
      return;
    }
    if (model) {
      setDay((current) => ({ ...current, model }));
      setPlanPreview((current) => ({ ...current, model }));
    }
  }

  async function handleKnowledgeSaved(source) {
    await loadDay(day.date, false);
    showNotice(`Indexed ${source.chunkCount} ${source.sourceUrl ? "attributed public" : "private"} chunk${source.chunkCount === 1 ? "" : "s"}.`);
  }

  async function handleAreaSaved() {
    await loadDay(day.date, false);
    await loadCalendar(month);
  }

  return (
    <div className="app-shell">
      <TabRail active={activeTab} onChange={navigate} />
      {activeTab === "today" ? (
        <TodayPage day={day} reports={reports} pool={pool} onCalendar={() => setActiveTab("calendar")} onPlans={openPlans} onGoals={() => navigate("goals")} onDomain={navigate} onChat={openConversation} onSuggestion={decideSuggestion} onDiscardAdvice={discardAdvice} onClearAdviceWeek={clearAdviceWeek} onItemSave={saveItem} onItemStatus={updateItemStatus} backendConnected={backendConnected} />
      ) : activeTab === "calendar" ? (
        <CalendarPage month={month} days={calendarDays} day={day} reports={reports} today={today} onMonth={chooseMonth} onSelect={chooseDate} onToday={() => chooseDate(today)} onPlans={openPlans} onDomain={navigate} onUpdate={updateEntry} onItemSave={saveItem} onItemStatus={updateItemStatus} onBuild={buildPlan} backendConnected={backendConnected} />
      ) : activeTab === "plans" ? (
        planPreview.planSetId ? <PlanDesk day={planPreview} reports={reports} readOnly={planPreview.date !== today} onVariant={selectVariant} onConfirm={confirm} onReplace={() => applyConfirmation(true)} onCancelReplace={() => setReplacing(false)} replacing={replacing} onChat={openConversation} backendConnected={backendConnected} /> : <EmptyPlanDesk day={day} today={today} onBuild={buildPlan} onSave={saveItem} onStatus={updateItemStatus} backendConnected={backendConnected} />
      ) : activeTab === "goals" ? (
        <GoalsPage day={day} onSave={saveGoal} backendConnected={backendConnected} onToday={() => navigate("today")} />
      ) : (
        <DomainPage section={activeTab} day={day} today={today} onToday={() => navigate("today")} onCalendar={() => setActiveTab("calendar")} onGoals={() => navigate("goals")} onChat={openConversation} onUpdate={updateEntry} onItemSave={saveItem} onItemStatus={updateItemStatus} backendConnected={backendConnected} onKnowledgeSaved={handleKnowledgeSaved} onAreaSaved={handleAreaSaved} />
      )}
      <button className="assistant-entry" onClick={() => openConversation("ask")} aria-label="Talk to Wellspent's local agents"><MessageSquare aria-hidden="true" /><span><strong>TALK TO WELLSPENT</strong><small>LOCAL AGENTS · YOUR DAY</small></span></button>
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
