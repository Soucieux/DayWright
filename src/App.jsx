import { useEffect, useRef, useState } from "react";
import { useWorkspace } from "./workspace";
import { dayRows } from "./today/dayRows";
import { TodayScreen } from "./today/TodayScreen";
import { PlansScreen } from "./plans/PlansScreen";
import { CalendarScreen } from "./calendar/CalendarScreen";
import { TaskSheet } from "./records/TaskSheet";
import { CatchUpSheet } from "./records/CatchUpSheet";
import { GoalsScreen } from "./records/GoalsScreen";
import { TasksScreen } from "./records/TasksScreen";
import { AreaScreen } from "./records/AreaScreen";
import { LibraryScreen } from "./library/LibraryScreen";
import { LibraryAddSheet } from "./library/LibrarySheets";
import { LibraryContext } from "./library/libraryContext";
import { BriefingContext, SourceBriefing } from "./library/SourceBriefing";
import { TalkPanel } from "./talk/TalkPanel";
import { GuideScreen, GuideSheet } from "./guide/Guide";
import { BottomBar, PhoneHeader, RecordsNav, TopBar } from "./shell/Shell";
import { SettingsSheet } from "./settings/SettingsSheet";
import { ModelsContext } from "./settings/NeedsModel";
import { SETTINGS_EVENT, avaOn } from "./settings/models";
import { SwitchOverlay } from "./settings/SwitchOverlay";
import { WorkspaceSwitchContext, useWorkspaceSwitch } from "./settings/useWorkspaceSwitch";
import { useCentredOpen } from "./ui/CentredSheet";
import { api } from "./api";
import { LanguageProvider, useI18n } from "./i18n";

/**
 * A short notice of what just happened, with its one action, such as Undo, when it offers one. The live
 * region stays in place so each new notice is read out.
 * @param {object} props
 * @param {{key?: string, values?: object, text?: string, action?: {key: string, run: () => void}}|null} props.notice -
 *   Interface text by key, with a status given by its key and names given as a list, or a message from the
 *   local service as it is; and its action's words and what it does.
 */
function Notice({ notice }) {
  const { t } = useI18n();
  const values = notice?.values && {
    ...notice.values,
    ...(notice.values.status ? { status: t(notice.values.status) } : {}),
    ...(notice.values.names ? { names: notice.values.names.join(t("listSeparator")) } : {}),
  };
  return (
    <div className="dw-notice-slot" role="status">
      {notice && (
        <p className="dw-notice">
          {notice.key ? t(notice.key, values) : notice.text}
          {notice.action && <button type="button" className="dw-notice-action" onClick={notice.action.run}>{t(notice.action.key)}</button>}
        </p>
      )}
    </div>
  );
}

/** The place each workspace section belongs to in the four-place navigation; the Guide is a place of its own. */
const PLACE_OF_TAB = {
  today: "today", plans: "today", calendar: "calendar", library: "library", guide: "guide",
  goals: "records", tasks: "records", learning: "records", life: "records", work: "records", project: "records",
};

/** Workspace sections shown inside Records. */
const RECORD_TABS = ["goals", "tasks", "learning", "life", "work", "project"];

function DayWrightApp() {
  const workspace = useWorkspace();
  // Opening the demo, going back, or resetting it: one switch for the window, which Settings closing doesn't end.
  const workspaceSwitch = useWorkspaceSwitch();
  const {
    today, day, month, calendarDays, reports, pool, backendConnected, notice, library, proposing, chooseMonth, updateEntry,
    discardAdvice, clearAdviceWeek, saveGoal, updateItemStatus, removeItem, decideSuggestion, removeGoal,
    handleConversationUpdate, refreshKnowledge, reportEnergy,
  } = workspace;
  const { t, language } = useI18n();
  // The menu bar's title is written in the interface's language, which only the interface knows.
  useEffect(() => {
    if (backendConnected) {
      api("/api/interface-language", { method: "PUT", body: JSON.stringify({ language }) }).catch(() => {});
    }
  }, [language, backendConnected]);
  const [activeTab, setActiveTab] = useState("today");
  const [plansFrom, setPlansFrom] = useState("today");
  const lastRecordsRef = useRef("goals");
  if (RECORD_TABS.includes(activeTab)) lastRecordsRef.current = activeTab;
  const place = PLACE_OF_TAB[activeTab];
  const [sheet, setSheet] = useState(null);
  const sheetRow = !sheet ? undefined
    : sheet.id === null ? null
      : dayRows(day).rows.find((row) => (sheet.itemId ? row.source?.id === sheet.itemId : row.id === sheet.id && row.kind === sheet.kind));
  // The Library's add sheet: whether it opens to write a note or import files, and the area and goal it starts linked to.
  const [libraryAdd, setLibraryAdd] = useState(null);
  // The screen whose Guide cards a "?" opened in a sheet.
  const [guideSheet, setGuideSheet] = useState(null);
  // Whether the sheet catching up on today's tasks at once is open, from Today or Tasks.
  const [catchingUp, setCatchingUp] = useState(false);
  // Settings, while it is open: the tab it opened on, and when, so each opening starts on its tab.
  const [settings, setSettings] = useState(null);
  // The Library item whose briefing shows in the side panel, and the name that opened it.
  const [briefing, setBriefing] = useState(null);
  // A centred panel is open: everything behind it is out of reach.
  const centredOpen = useCentredOpen();
  // Ava answers only with her model ready; while she can't, nothing sends the user to her.
  const ava = avaOn(backendConnected, day.model);
  // The card one of Ava's See Guide links asked the Guide to show.
  const [guideFocus, setGuideFocus] = useState(null);
  // A goal's sheet waits behind a task's sheet, a briefing or the Guide's sheet opened over it; a centred panel opens
  // over it instead.
  const sheetOpen = sheetRow !== undefined || guideSheet !== null || briefing !== null;
  const [conversationOpen, setConversationOpen] = useState(false);
  const [conversationPrompt, setConversationPrompt] = useState(null);
  const [listArea, setListArea] = useState("all");

  /**
   * Open a task's side panel, in place of the Guide's or a briefing, so one side panel shows at a time.
   * @param {object} value - Which task to show, or `{id: null}` for a new one.
   */
  function openSheet(value) {
    setLibraryAdd(null);
    setGuideSheet(null);
    setBriefing(null);
    setCatchingUp(false);
    setSettings(null);
    setSheet(value);
  }

  /** Catch up on today's tasks at once, from Today or Tasks, centred over any side panel. */
  function openCatchUp() {
    setLibraryAdd(null);
    setSettings(null);
    setCatchingUp(true);
  }

  /**
   * Open Settings, centred, as the app menu's Settings… (⌘,), the menu bar's, the gear and every Open Settings ask.
   * @param {CustomEvent} [event] - The event asking, whose `tab` names the tab to open on.
   */
  function openSettingsSheet(event) {
    setLibraryAdd(null);
    setCatchingUp(false);
    setSettings({ tab: event?.detail?.tab || "models", at: Date.now() });
  }

  /**
   * Add to the Library, from the Library or Learn's + Add, centred over any side panel.
   * @param {"note"|"files"} kind - Whether it opens to write a note or to import files.
   */
  function addToLibrary(kind) {
    setCatchingUp(false);
    setSettings(null);
    setLibraryAdd({ kind });
  }

  /**
   * Show a screen's Guide cards in a sheet, as its "?" asks: a goal's sheet waits behind it.
   * @param {string} screen - The screen, as the Guide names it.
   */
  function openGuideSheet(screen) {
    setSheet(null);
    setBriefing(null);
    setLibraryAdd(null);
    setCatchingUp(false);
    setSettings(null);
    setGuideSheet(screen);
  }

  /**
   * Show a Library item's briefing in the side panel, or swap it in for the one on show; the Guide's sheet closes, and
   * a task's or a goal's waits beneath it.
   * @param {object} source - The item.
   * @param {HTMLElement} opener - The name that opened it, which focus returns to.
   */
  function openBriefing(source, opener) {
    setGuideSheet(null);
    setBriefing({ id: source.id, source, opener });
  }

  /**
   * Show one card in the Guide, as a See Guide link in Ava's answer asks, closing Ava so it is in view.
   * @param {string} card - The card's id.
   */
  function openGuide(card) {
    setConversationOpen(false);
    setGuideFocus({ card, at: Date.now() });
    navigate("guide");
  }

  /** Show the Guide from its link beside the language switch, with no card asked for. */
  function showGuide() {
    setGuideFocus(null);
    navigate("guide");
  }

  /**
   * Show a section, closing any sheet.
   * @param {string} section - The section, as PLACE_OF_TAB names it.
   * @param {string} [area="all"] - The area Tasks or the Library opens filtered to, as an area's See all sets it.
   */
  async function navigate(section, area = "all") {
    setSheet(null);
    setLibraryAdd(null);
    setGuideSheet(null);
    setBriefing(null);
    setCatchingUp(false);
    setListArea(area);
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

  /**
   * Open Ava with a request typed into its box, to send or change before sending; or, for a button that
   * asks for one thing, such as Continue next session, sent at once.
   * @param {string} [text] - The request; Ava opens empty without one.
   * @param {boolean} [send=false] - Send it at once.
   * @param {string|null} [date=null] - The day a request sent at once is about, when not the day on show, as
   *   Catch up from Patterns asks from the earliest day with a task needing a status.
   */
  function askAva(text, send = false, date = null) {
    if (text) setConversationPrompt({ id: Date.now(), text, send, date });
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
      // Ava stays as she is while a centred panel is open over her.
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k" && !centredOpen) {
        event.preventDefault();
        toggleTalk();
      }
      // ⌘, opens Settings in a browser too, as the app menu's Settings… does in the Mac app.
      if ((event.metaKey || event.ctrlKey) && event.key === ",") {
        event.preventDefault();
        openSettingsSheet();
      }
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener(SETTINGS_EVENT, openSettingsSheet);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(SETTINGS_EVENT, openSettingsSheet);
    };
  });

  // Another plan comes from the day's plans while the service answers but Ava can't, else from Ava, who says why
  // she can't answer when the service doesn't.
  const askOtherPlan = () => (backendConnected && !ava ? openPlans() : openConversation("avaAskOtherPlan"));

  return (
    <WorkspaceSwitchContext.Provider value={workspaceSwitch}>
    <LibraryContext.Provider value={{ items: library.items || [], folders: library.folders, backendConnected,
      refresh: () => refreshKnowledge(), tasksMade: workspace.tasksMade }}>
    <ModelsContext.Provider value={{ models: day.models, ava, connected: backendConnected }}>
    <BriefingContext.Provider value={{ open: openBriefing, shown: briefing?.id ?? null }}>
    <div className="dw-app" inert={workspaceSwitch.active || centredOpen || undefined}>
      <TopBar place={place} onPlace={goToPlace} backendConnected={backendConnected} demoMode={Boolean(day.demoMode)} model={day.model}
        talkOpen={conversationOpen} unread={Boolean(day.unreadNotices)} ava={ava} onTalk={toggleTalk} onGuide={showGuide} />
      <PhoneHeader place={place} backendConnected={backendConnected} demoMode={Boolean(day.demoMode)} model={day.model}
        onGuide={showGuide} />
      <div className={`dw-main${place === "records" ? " dw-with-side" : ""}`}>
      {place === "records" && <RecordsNav section={activeTab} goalCount={day.goals.length} onSection={navigate} />}
      <div className="dw-content">
      {activeTab === "today" ? (
        <TodayScreen day={day} reports={reports} pool={pool} backendConnected={backendConnected} proposing={proposing} onStatus={reportRow} onPropose={buildPlan}
          onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })} onPlans={openPlans} onDeselect={workspace.unsetPlan}
          onGoals={() => navigate("goals")}
          onAddTask={() => openSheet({ id: null })}
          onReplace={askOtherPlan} onDismissAdvice={discardAdvice} onDecide={decideSuggestion}
          onEnergy={reportEnergy} onGuide={openGuideSheet}
          onAskAva={askAva} onDismissYesterday={workspace.dismissYesterdayNotice} onCatchUp={openCatchUp}
          onPause={() => workspace.pauseDay(true)} onResume={() => workspace.pauseDay(false)} />
      ) : activeTab === "calendar" ? (
        <CalendarScreen month={month} days={calendarDays} day={day} today={today} reports={reports} pool={pool}
          backendConnected={backendConnected} onMonth={chooseMonth} onSelect={chooseDate} onToday={() => chooseDate(today)}
          onOpenPlans={openPlans} onAddTask={() => openSheet({ id: null })}
          onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })} onAsk={() => openConversation()} onAskAva={askAva}
          onDecide={decideSuggestion} onDismissAdvice={discardAdvice} onClearWeek={clearAdviceWeek} onGuide={openGuideSheet} />
      ) : activeTab === "plans" ? (
        <PlansScreen key={day.date} day={day} today={today} backendConnected={backendConnected} proposing={proposing}
          backLabel={plansFrom === "calendar" ? t("navCalendar") : t("navToday")} onBack={leavePlans}
          onAskDifferent={() => openConversation("avaAskOtherPlan")} onPropose={buildPlan} onProposeAgain={workspace.reproposePlans}
          onSet={setPlan} onGuide={openGuideSheet} />
      ) : activeTab === "goals" ? (
        <GoalsScreen day={day} today={today} backendConnected={backendConnected} library={library.items} onSaveGoal={saveGoal} onRemoveGoal={removeGoal}
          onAddTask={(goal) => addTaskToday({ domain: goal.domain, goalId: goal.id })}
          sheetOpen={sheetOpen} onEditTask={(item) => openTask(item, true)} onRemoveTask={removeItem} onGuide={openGuideSheet}
          onOpenTask={(item) => openTask(item)} onAskAva={askAva} />
      ) : activeTab === "tasks" ? (
        <TasksScreen key={listArea} day={day} today={today} backendConnected={backendConnected} initialArea={listArea}
          onOpenTask={openTask} onAddTask={() => addTaskToday()} onGuide={openGuideSheet} onCatchUp={openCatchUp} />
      ) : activeTab === "library" ? (
        <LibraryScreen day={day} today={today} backendConnected={backendConnected} library={library}
          onAdd={(kind) => addToLibrary(kind)} onAskAva={askAva} onChanged={refreshKnowledge} onGuide={openGuideSheet} />
      ) : activeTab === "guide" ? (
        <GuideScreen focus={guideFocus} demoMode={Boolean(day.demoMode)} />
      ) : (
        <AreaScreen key={activeTab} domain={activeTab} day={day} today={today} backendConnected={backendConnected}
          onRecords={() => navigate("goals")} onToday={() => workspace.showToday()} onTodayScreen={() => navigate("today")}
          onAddTask={(defaults) => openSheet({ id: null, defaults })} onOpenRow={(row) => openSheet({ id: row.id, kind: row.kind })}
          onOpenTask={(item) => openTask(item)} onStatus={reportRow} onSeeAll={() => navigate("tasks", activeTab)}
          onAskAva={askAva} onSaveGoal={saveGoal} onEditTask={(item) => openTask(item, true)} onRemoveTask={removeItem}
          library={library.items} onAddToLibrary={() => addToLibrary("note")} onSeeLibrary={() => navigate("library", activeTab)}
          sheetOpen={sheetOpen} onGuide={openGuideSheet} />
      )}
      </div>
      <div id="dw-sheet-slot" className="dw-sheet-slot" />
      {sheetRow !== undefined && (
        <TaskSheet key={sheet.id || sheet.itemId || "new"} row={sheetRow} date={day.date} today={today} goals={day.goals} defaults={sheet.defaults}
          startEditing={Boolean(sheet.editing)} backendConnected={backendConnected} hidden={briefing !== null}
          onSave={saveItem} onRemove={removeItem} onStatus={reportRow} onAskAva={askAva} onGuide={openGuideSheet} onUpdated={refreshKnowledge}
          onClose={() => setSheet(null)}
          onReplace={() => { setSheet(null); askOtherPlan(); }} />
      )}
      {libraryAdd && (
        <LibraryAddSheet kind={libraryAdd.kind} backendConnected={backendConnected}
          onSaved={refreshKnowledge} onClose={() => setLibraryAdd(null)} />
      )}
      {guideSheet && <GuideSheet screen={guideSheet} onClose={() => setGuideSheet(null)} />}
      {briefing && (
        <SourceBriefing key={briefing.id} source={(library.items || []).find((item) => item.id === briefing.id) || briefing.source}
          opener={briefing.opener} onClose={() => setBriefing(null)} />
      )}
      {catchingUp && <CatchUpSheet backendConnected={backendConnected} onSave={workspace.catchUp} onClose={() => setCatchingUp(false)} />}
      {settings && <SettingsSheet key={settings.at} tab={settings.tab} backendConnected={backendConnected} demoMode={Boolean(day.demoMode)}
        onChanged={workspace.reloadDay} onClose={() => setSettings(null)} />}
      <TalkPanel open={conversationOpen} day={day} today={today} topic={activeTab === "plans" ? "plans" : place}
        prompt={conversationPrompt} backendConnected={backendConnected} onClose={() => setConversationOpen(false)}
        onUpdated={handleConversationUpdate} onSeen={workspace.readNotices} onNotices={workspace.showNotices} onGuide={openGuide}
        onOpenPlans={async () => { setConversationOpen(false); await workspace.showToday(); openPlans(); }} />
      </div>
      <BottomBar place={place} onPlace={goToPlace} talkOpen={conversationOpen} unread={Boolean(day.unreadNotices)} ava={ava}
        onTalk={toggleTalk} />
      <Notice notice={notice} />
    </div>
    {workspaceSwitch.active && <SwitchOverlay {...workspaceSwitch} />}
    </BriefingContext.Provider>
    </ModelsContext.Provider>
    </LibraryContext.Provider>
    </WorkspaceSwitchContext.Provider>
  );
}

export function App() {
  return <LanguageProvider><DayWrightApp /></LanguageProvider>;
}
