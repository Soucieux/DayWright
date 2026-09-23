import { useEffect, useRef, useState } from "react";
import { Check, MessageSquare, Mic, Pin, Send, Sparkles, Target, X } from "lucide-react";
import { api } from "./api";
import { DomainRecordsBoard } from "./DomainRecords";
import { useWorkspace } from "./workspace";
import { dayRows } from "./today/dayRows";
import { TodayScreen } from "./today/TodayScreen";
import { PlansScreen } from "./plans/PlansScreen";
import { CalendarScreen } from "./calendar/CalendarScreen";
import { TaskSheet } from "./records/TaskSheet";
import { linkableGoals, taskDraft, taskPayload } from "./records/taskDraft";
import { BottomBar, PhoneHeader, RecordsNav, TopBar } from "./shell/Shell";
import { beginVoiceCapture } from "./voice";
import { LanguageProvider, useI18n } from "./i18n";

const domainMeta = {
  learning: { label: "Learn", color: "#f1512e" },
  life: { label: "Life", color: "#245fe5" },
  finance: { label: "Finance", color: "#24855f" },
  rest: { label: "Rest", color: "#66615c" },
};

const modeCopy = {
  ask: ["Ask", "Understand the plan or weigh a tradeoff."],
  adjust: ["Adjust", "Describe a change. DayWright will propose it for confirmation."],
  report: ["Report", "Talk through what happened; completion remains explicit."],
};

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

/** Collect or edit one dated task without silently turning it into a plan. */
function DayItemForm({ date, goals, item, defaultDomain = "life", defaultGoalId = "", onSave, backendConnected, onCancel }) {
  const { t } = useI18n();
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setDraft(taskDraft(item, date, defaultDomain, defaultGoalId)), [date, item, defaultDomain, defaultGoalId]);

  async function submit(event) {
    event.preventDefault();
    if (!backendConnected || saving) return;
    setSaving(true);
    setError("");
    try {
      await onSave(taskPayload(draft), item?.id);
      if (!item) setDraft((current) => ({ ...current, title: "", detail: "",
        constraintKind: "flexible", repeatKind: "none", protected: false, goalId: "" }));
      else onCancel();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  }

  const matchingGoals = linkableGoals(goals, draft.domain);
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
    today, day, month, calendarDays, reports, pool, backendConnected, notice, chooseMonth, updateEntry,
    discardAdvice, clearAdviceWeek, saveGoal, updateItemStatus, removeItem, decideSuggestion, removeGoal,
    handleConversationUpdate, handleKnowledgeSaved, handleAreaSaved,
  } = workspace;
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState("today");
  const lastRecordsRef = useRef("goals");
  if (RECORD_TABS.includes(activeTab)) lastRecordsRef.current = activeTab;
  const place = PLACE_OF_TAB[activeTab];
  const [sheet, setSheet] = useState(null);
  const sheetRow = !sheet ? undefined
    : sheet.id === null ? null
      : dayRows(day).rows.find((row) => row.id === sheet.id && row.kind === sheet.kind);
  const [conversationOpen, setConversationOpen] = useState(false);
  const [conversationMode, setConversationMode] = useState("ask");

  async function navigate(section) {
    setSheet(null);
    setActiveTab(section);
    if (section === "today") await workspace.showToday();
  }

  function openPlans() {
    setActiveTab("plans");
  }

  /** Leave the plans for where they were opened from: Today for today, Calendar for any other day. */
  function leavePlans() {
    if (day.date === today) navigate("today");
    else setActiveTab("calendar");
  }

  async function setPlan(variantId, replaceExisting) {
    if (await workspace.setPlan(variantId, replaceExisting)) leavePlans();
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

  function reportRow(row, status) {
    if (row.kind === "entry") updateEntry(row.id, status);
    else updateItemStatus(row, status);
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
      <div className="dw-content">
      {activeTab === "today" ? (
        <TodayScreen day={day} pool={pool} backendConnected={backendConnected} onStatus={reportRow} onPropose={buildPlan}
          onOpenRow={(row) => setSheet({ id: row.id, kind: row.kind })} onPlans={openPlans} onGoals={() => navigate("goals")}
          onAddTask={() => setSheet({ id: null })}
          onReplace={() => openConversation("adjust")} onDismissAdvice={discardAdvice} onDecide={decideSuggestion} />
      ) : activeTab === "calendar" ? (
        <CalendarScreen month={month} days={calendarDays} day={day} today={today} reports={reports} pool={pool}
          backendConnected={backendConnected} onMonth={chooseMonth} onSelect={chooseDate} onToday={() => chooseDate(today)}
          onOpenPlans={openPlans} onOpenToday={() => navigate("today")} onAddTask={() => setSheet({ id: null })}
          onOpenRow={(row) => setSheet({ id: row.id, kind: row.kind })} onAsk={() => openConversation("ask")}
          onDecide={decideSuggestion} onDismissAdvice={discardAdvice} onClearWeek={clearAdviceWeek} />
      ) : activeTab === "plans" ? (
        <PlansScreen key={day.date} day={day} today={today} backendConnected={backendConnected}
          backLabel={day.date === today ? t("navToday") : t("navCalendar")} onBack={leavePlans}
          onAskDifferent={() => openConversation("adjust")} onPropose={buildPlan} onSet={setPlan} />
      ) : activeTab === "goals" ? (
        <GoalsPage day={day} onSave={saveGoal} onItemSave={saveItem} onRemove={removeGoal} backendConnected={backendConnected} onToday={() => navigate("today")} />
      ) : (
        <DomainPage section={activeTab} day={day} today={today} onToday={() => navigate("today")} onCalendar={() => setActiveTab("calendar")} onGoals={() => navigate("goals")} onChat={openConversation} onUpdate={updateEntry} onItemSave={saveItem} onItemStatus={updateItemStatus} onItemRemove={removeItem} backendConnected={backendConnected} onKnowledgeSaved={handleKnowledgeSaved} onAreaSaved={handleAreaSaved} />
      )}
      </div>
      {sheetRow !== undefined && (
        <TaskSheet key={sheet.id || "new"} row={sheetRow} date={day.date} goals={day.goals} backendConnected={backendConnected}
          onSave={saveItem} onRemove={removeItem} onStatus={reportRow} onClose={() => setSheet(null)}
          onReplace={() => { setSheet(null); openConversation("adjust"); }} />
      )}
      </div>
      <BottomBar place={place} onPlace={goToPlace} talkOpen={conversationOpen} onTalk={toggleTalk} />
      <ConversationDrawer
        open={conversationOpen}
        onClose={() => setConversationOpen(false)}
        day={day}
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
