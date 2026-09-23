import { useEffect, useRef, useState } from "react";
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
import { TalkPanel } from "./talk/TalkPanel";
import { BottomBar, PhoneHeader, RecordsNav, TopBar } from "./shell/Shell";
import { LanguageProvider, useI18n } from "./i18n";

/**
 * A short notice of what just happened. The live region stays in place so each new notice is read out.
 * @param {object} props
 * @param {{key?: string, values?: object, text?: string}|null} props.notice - Interface text by key,
 *   or a message from the local service as it is.
 */
function Notice({ notice }) {
  const { t } = useI18n();
  const values = notice?.values?.status ? { ...notice.values, status: t(notice.values.status) } : notice?.values;
  return (
    <div className="dw-notice-slot" role="status">
      {notice && <p className="dw-notice">{notice.key ? t(notice.key, values) : notice.text}</p>}
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
          onReplace={() => openConversation("adjust")} onDismissAdvice={discardAdvice} onDecide={decideSuggestion}
          onModel={(model) => handleConversationUpdate(model)} />
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
      <TalkPanel open={conversationOpen} day={day} today={today} place={place} mode={conversationMode} onMode={setConversationMode}
        backendConnected={backendConnected} onClose={() => setConversationOpen(false)} onUpdated={handleConversationUpdate} />
      </div>
      <BottomBar place={place} onPlace={goToPlace} talkOpen={conversationOpen} onTalk={toggleTalk} />
      <Notice notice={notice} />
    </div>
  );
}

export function App() {
  return <LanguageProvider><DayWrightApp /></LanguageProvider>;
}
