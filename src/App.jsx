import { useEffect, useRef, useState } from "react";
import { Mic, Send, Sparkles, X } from "lucide-react";
import { api } from "./api";
import { useWorkspace } from "./workspace";
import { dayRows } from "./today/dayRows";
import { TodayScreen } from "./today/TodayScreen";
import { PlansScreen } from "./plans/PlansScreen";
import { CalendarScreen } from "./calendar/CalendarScreen";
import { TaskSheet } from "./records/TaskSheet";
import { GoalsScreen } from "./records/GoalsScreen";
import { TasksScreen } from "./records/TasksScreen";
import { AreaScreen } from "./records/AreaScreen";
import { LibraryScreen } from "./library/LibraryScreen";
import { NetworkLogSheet } from "./library/NetworkLog";
import { entriesOn } from "./library/libraryData";
import { BottomBar, PhoneHeader, RecordsNav, TopBar } from "./shell/Shell";
import { beginVoiceCapture } from "./voice";
import { LanguageProvider, useI18n } from "./i18n";

const modeCopy = {
  ask: ["Ask", "Understand the plan or weigh a tradeoff."],
  adjust: ["Adjust", "Describe a change. DayWright will propose it for confirmation."],
  report: ["Report", "Talk through what happened; completion remains explicit."],
};

function Icon({ name }) {
  const icons = { spark: Sparkles, mic: Mic, send: Send, close: X };
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

/** The place each workspace section belongs to in the four-place navigation. */
const PLACE_OF_TAB = {
  today: "today", plans: "today", calendar: "calendar", library: "library",
  goals: "records", tasks: "records", learning: "records", life: "records", finance: "records",
};

/** Workspace sections shown inside Records. */
const RECORD_TABS = ["goals", "tasks", "learning", "life", "finance"];

function DayWrightApp() {
  const workspace = useWorkspace();
  const {
    today, day, month, calendarDays, reports, pool, backendConnected, notice, networkLog, chooseMonth, updateEntry,
    discardAdvice, clearAdviceWeek, saveGoal, updateItemStatus, removeItem, decideSuggestion, removeGoal,
    handleConversationUpdate, refreshKnowledge, loadNetworkLog, handleAreaSaved,
  } = workspace;
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState("today");
  const lastRecordsRef = useRef("goals");
  if (RECORD_TABS.includes(activeTab)) lastRecordsRef.current = activeTab;
  const place = PLACE_OF_TAB[activeTab];
  const [sheet, setSheet] = useState(null);
  const sheetRow = !sheet ? undefined
    : sheet.id === null ? null
      : dayRows(day).rows.find((row) => (sheet.itemId ? row.source?.id === sheet.itemId : row.id === sheet.id && row.kind === sheet.kind));
  const [taskGoal, setTaskGoal] = useState(null);
  const [logOpen, setLogOpen] = useState(false);
  const lookupsToday = entriesOn(networkLog, today).length;
  const [conversationOpen, setConversationOpen] = useState(false);
  const [conversationMode, setConversationMode] = useState("ask");

  /**
   * Open a task's sheet, closing the network log so one sheet shows at a time.
   * @param {object} value - Which task to show, or `{id: null}` for a new one.
   */
  function openSheet(value) {
    setLogOpen(false);
    setSheet(value);
  }

  /** Show the network log, closing any task sheet so one sheet shows at a time. */
  function openLog() {
    setSheet(null);
    setLogOpen(true);
  }

  async function navigate(section) {
    setSheet(null);
    setLogOpen(false);
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

  /**
   * Show a task from a list that spans days: load its day, then open its details.
   * @param {object} item - The task.
   */
  async function openTask(item) {
    await workspace.showDate(item.date);
    openSheet({ itemId: item.id });
  }

  /**
   * Record a new task today, starting in an area or for a goal.
   * @param {{domain?: string, goalId?: string}} [defaults] - The new task's area and goal.
   */
  async function addTaskToday(defaults = {}) {
    if (day.date !== today) await workspace.showToday();
    openSheet({ id: null, defaults });
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
      <TopBar place={place} onPlace={goToPlace} backendConnected={backendConnected} demoMode={Boolean(day.demoMode)} model={day.model}
        lookupsToday={lookupsToday} onNetwork={openLog} talkOpen={conversationOpen} onTalk={toggleTalk} />
      <PhoneHeader backendConnected={backendConnected} demoMode={Boolean(day.demoMode)} model={day.model}
        lookupsToday={lookupsToday} onNetwork={openLog} />
      <div className={`dw-main${place === "records" ? " dw-with-side" : ""}`}>
      {place === "records" && <RecordsNav section={activeTab} goalCount={day.goals.length} onSection={(section) => { setTaskGoal(null); navigate(section); }} />}
      <div className="dw-content">
      {activeTab === "today" ? (
        <TodayScreen day={day} pool={pool} backendConnected={backendConnected} onStatus={reportRow} onPropose={buildPlan}
          onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })} onPlans={openPlans} onGoals={() => navigate("goals")}
          onAddTask={() => openSheet({ id: null })}
          onReplace={() => openConversation("adjust")} onDismissAdvice={discardAdvice} onDecide={decideSuggestion} />
      ) : activeTab === "calendar" ? (
        <CalendarScreen month={month} days={calendarDays} day={day} today={today} reports={reports} pool={pool}
          backendConnected={backendConnected} onMonth={chooseMonth} onSelect={chooseDate} onToday={() => chooseDate(today)}
          onOpenPlans={openPlans} onOpenToday={() => navigate("today")} onAddTask={() => openSheet({ id: null })}
          onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })} onAsk={() => openConversation("ask")}
          onDecide={decideSuggestion} onDismissAdvice={discardAdvice} onClearWeek={clearAdviceWeek} />
      ) : activeTab === "plans" ? (
        <PlansScreen key={day.date} day={day} today={today} backendConnected={backendConnected}
          backLabel={day.date === today ? t("navToday") : t("navCalendar")} onBack={leavePlans}
          onAskDifferent={() => openConversation("adjust")} onPropose={buildPlan} onSet={setPlan} />
      ) : activeTab === "goals" ? (
        <GoalsScreen day={day} today={today} backendConnected={backendConnected} onSaveGoal={saveGoal} onRemoveGoal={removeGoal}
          onAddTask={(goal) => addTaskToday({ domain: goal.domain, goalId: goal.id })}
          onShowTasks={(goal) => { setTaskGoal(goal); navigate("tasks"); }} />
      ) : activeTab === "tasks" ? (
        <TasksScreen day={day} today={today} backendConnected={backendConnected} goal={taskGoal} onClearGoal={() => setTaskGoal(null)}
          onOpenTask={openTask} onAddTask={() => addTaskToday()} />
      ) : activeTab === "library" ? (
        <LibraryScreen day={day} today={today} backendConnected={backendConnected} networkLog={networkLog}
          onAskTalk={() => openConversation("ask")} onOpenLog={openLog} onChanged={refreshKnowledge} onNetwork={loadNetworkLog} />
      ) : (
        <AreaScreen key={activeTab} domain={activeTab} day={day} today={today} backendConnected={backendConnected}
          onRecords={() => navigate("goals")} onToday={() => workspace.showToday()}
          onAddTask={(domain) => openSheet({ id: null, defaults: { domain } })} onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })}
          onStatus={reportRow} onAreaSaved={handleAreaSaved} />
      )}
      </div>
      <div id="dw-sheet-slot" className="dw-sheet-slot" />
      {sheetRow !== undefined && (
        <TaskSheet key={sheet.id || sheet.itemId || "new"} row={sheetRow} date={day.date} goals={day.goals} defaults={sheet.defaults} backendConnected={backendConnected}
          onSave={saveItem} onRemove={removeItem} onStatus={reportRow} onClose={() => setSheet(null)}
          onReplace={() => { setSheet(null); openConversation("adjust"); }} />
      )}
      {logOpen && <NetworkLogSheet entries={networkLog} onClose={() => setLogOpen(false)} />}
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
