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
  goals: "records", tasks: "records", learning: "records", life: "records", work: "records", project: "records",
};

/** Workspace sections shown inside Records. */
const RECORD_TABS = ["goals", "tasks", "learning", "life", "work", "project"];

function DayWrightApp() {
  const workspace = useWorkspace();
  const {
    today, day, month, calendarDays, reports, pool, backendConnected, notice, networkLog, proposing, chooseMonth, updateEntry,
    discardAdvice, clearAdviceWeek, saveGoal, updateItemStatus, removeItem, decideSuggestion, removeGoal,
    handleConversationUpdate, refreshKnowledge, loadNetworkLog, handleAreaSaved,
  } = workspace;
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState("today");
  const [plansFrom, setPlansFrom] = useState("today");
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
  const [conversationPrompt, setConversationPrompt] = useState(null);

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

  /** Show the day's plans, remembering whether Today or Calendar opened them. */
  function openPlans() {
    if (activeTab !== "plans") setPlansFrom(activeTab);
    setActiveTab("plans");
  }

  /** Leave the plans for where they were opened from. */
  function leavePlans() {
    if (plansFrom === "calendar") setActiveTab("calendar");
    else navigate("today");
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
    if (await workspace.buildPlan()) openPlans();
  }

  /**
   * Show a task from a list that spans days: load its day, then open its details, or its form.
   * @param {object} item - The task.
   * @param {boolean} [editing=false] - Open straight into its form, closing when that is done.
   */
  async function openTask(item, editing = false) {
    await workspace.showDate(item.date);
    openSheet({ itemId: item.id, editing });
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

  /**
   * Open Ava, with a question ready in its box when a screen opens it for one.
   * @param {string} [promptKey] - The question's message key.
   */
  function openConversation(promptKey) {
    if (promptKey) setConversationPrompt({ id: Date.now(), text: t(promptKey) });
    setConversationOpen(true);
  }

  function goToPlace(next) {
    navigate(next === "records" ? lastRecordsRef.current : next);
  }

  function toggleTalk() {
    if (conversationOpen) setConversationOpen(false);
    else openConversation();
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
        lookupsToday={lookupsToday} onNetwork={openLog} talkOpen={conversationOpen} unread={Boolean(day.unreadNotices)}
        onTalk={toggleTalk} />
      <PhoneHeader backendConnected={backendConnected} demoMode={Boolean(day.demoMode)} model={day.model}
        lookupsToday={lookupsToday} onNetwork={openLog} />
      <div className={`dw-main${place === "records" ? " dw-with-side" : ""}`}>
      {place === "records" && <RecordsNav section={activeTab} goalCount={day.goals.length} onSection={(section) => { setTaskGoal(null); navigate(section); }} />}
      <div className="dw-content">
      {activeTab === "today" ? (
        <TodayScreen day={day} reports={reports} pool={pool} backendConnected={backendConnected} proposing={proposing} onStatus={reportRow} onPropose={buildPlan}
          onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })} onPlans={openPlans} onDeselect={workspace.unsetPlan}
          onGoals={() => navigate("goals")}
          onAddTask={() => openSheet({ id: null })}
          onReplace={() => openConversation("avaAskOtherPlan")} onDismissAdvice={discardAdvice} onDecide={decideSuggestion}
          onModel={(model) => handleConversationUpdate(model)} />
      ) : activeTab === "calendar" ? (
        <CalendarScreen month={month} days={calendarDays} day={day} today={today} reports={reports} pool={pool}
          backendConnected={backendConnected} onMonth={chooseMonth} onSelect={chooseDate} onToday={() => chooseDate(today)}
          onOpenPlans={openPlans} onAddTask={() => openSheet({ id: null })}
          onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })} onAsk={() => openConversation()}
          onDecide={decideSuggestion} onDismissAdvice={discardAdvice} onClearWeek={clearAdviceWeek} />
      ) : activeTab === "plans" ? (
        <PlansScreen key={day.date} day={day} today={today} backendConnected={backendConnected} proposing={proposing}
          backLabel={plansFrom === "calendar" ? t("navCalendar") : t("navToday")} onBack={leavePlans}
          onAskDifferent={() => openConversation("avaAskOtherPlan")} onPropose={buildPlan} onProposeAgain={workspace.reproposePlans}
          onSet={setPlan} />
      ) : activeTab === "goals" ? (
        <GoalsScreen day={day} today={today} backendConnected={backendConnected} onSaveGoal={saveGoal} onRemoveGoal={removeGoal}
          onAddTask={(goal) => addTaskToday({ domain: goal.domain, goalId: goal.id })}
          onShowTasks={(goal) => { setTaskGoal(goal); navigate("tasks"); }}
          taskOpen={sheetRow !== undefined} onEditTask={(item) => openTask(item, true)} />
      ) : activeTab === "tasks" ? (
        <TasksScreen day={day} today={today} backendConnected={backendConnected} goal={taskGoal} onClearGoal={() => setTaskGoal(null)}
          onOpenTask={openTask} onAddTask={() => addTaskToday()} />
      ) : activeTab === "library" ? (
        <LibraryScreen day={day} today={today} backendConnected={backendConnected} networkLog={networkLog}
          onAskTalk={() => openConversation()} onOpenLog={openLog} onChanged={refreshKnowledge} onNetwork={loadNetworkLog} />
      ) : (
        <AreaScreen key={activeTab} domain={activeTab} day={day} today={today} backendConnected={backendConnected}
          onRecords={() => navigate("goals")} onToday={() => workspace.showToday()}
          onAddTask={(domain) => openSheet({ id: null, defaults: { domain } })} onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })}
          onStatus={reportRow} onAreaSaved={handleAreaSaved} />
      )}
      </div>
      <div id="dw-sheet-slot" className="dw-sheet-slot" />
      {sheetRow !== undefined && (
        <TaskSheet key={sheet.id || sheet.itemId || "new"} row={sheetRow} date={day.date} today={today} goals={day.goals} defaults={sheet.defaults}
          startEditing={Boolean(sheet.editing)} backendConnected={backendConnected}
          onSave={saveItem} onRemove={removeItem} onStatus={reportRow} onClose={() => setSheet(null)}
          onReplace={() => { setSheet(null); openConversation("avaAskOtherPlan"); }} />
      )}
      {logOpen && <NetworkLogSheet entries={networkLog} onClose={() => setLogOpen(false)} />}
      <TalkPanel open={conversationOpen} day={day} today={today} topic={activeTab === "plans" ? "plans" : place}
        prompt={conversationPrompt} backendConnected={backendConnected} onClose={() => setConversationOpen(false)}
        onUpdated={handleConversationUpdate} onSeen={workspace.readNotices} onNotices={workspace.showNotices} />
      </div>
      <BottomBar place={place} onPlace={goToPlace} talkOpen={conversationOpen} unread={Boolean(day.unreadNotices)}
        onTalk={toggleTalk} />
      <Notice notice={notice} />
    </div>
  );
}

export function App() {
  return <LanguageProvider><DayWrightApp /></LanguageProvider>;
}
