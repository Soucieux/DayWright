import { useEffect, useMemo, useRef, useState } from "react";
import { api, getCalendar, getDay, getSummaries } from "./api";
import { refusalKey } from "./serviceText";
import { latestReading } from "./ui/visuals";

/** How long a notice stays on screen before it clears itself. */
const NOTICE_DURATION_MS = 2800;

/** Return today's date as YYYY-MM-DD in the Mac's local time. */
function localToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

/**
 * Build the day shown before the local service answers, or for a date with no records.
 * @param {string} date - The YYYY-MM-DD date this empty day stands for.
 * @returns {object} A day with no plan, records or messages, and the idle model label.
 */
function emptyDay(date) {
  return {
    date, planSetId: null, planSource: null, selectedVariantId: null,
    confirmedVariantId: null, variants: [], entries: [], suggestion: null,
    balance: { learning: 0, life: 0, work: 0, project: 0 },
    hardConstraints: [], plannerNotes: [], dayItems: [], goals: [], messages: [],
    model: { label: "Local model starts when you ask", running: false },
    rag: { vectorStore: { sourceCount: 0 } },
  };
}

/**
 * Summarise the unsaved preview day as one calendar cell while the local service is unreachable.
 * @param {object} day - The preview day held in memory.
 * @returns {object} A calendar cell in the shape the local service returns.
 */
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

/**
 * Own the workspace's data and every action that reads or writes it: the selected day, the calendar
 * month, Summary reports, the Library's notes and files, and the local service connection.
 *
 * Navigation belongs to the interface. Actions only load data and report what happened (`saveItem`,
 * `buildPlan` and `setPlan` return their outcome), so each interface decides where to go next.
 * @returns {object} Workspace state and actions.
 */
export function useWorkspace() {
  const today = useMemo(localToday, []);
  const previewTodayRef = useRef(emptyDay(today));
  const summaryRequestRef = useRef(0);
  const noticeTimerRef = useRef(0);
  const [day, setDay] = useState(() => emptyDay(today));
  const [month, setMonth] = useState(today.slice(0, 7));
  const [calendarDays, setCalendarDays] = useState([]);
  const [reports, setReports] = useState(null);
  const [pool, setPool] = useState(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [notice, setNotice] = useState(null);
  // The Library's items, newest first, null until they load, with the reason when they can't; its
  // connected folders, Open with's app for each kind of file, and whether Obsidian is installed.
  const [library, setLibrary] = useState({ items: null, folders: [], openWith: {}, obsidian: false, error: "" });
  const [proposing, setProposing] = useState(false);

  /**
   * Show a short notice, then clear it.
   * @param {{key?: string, values?: object, text?: string}} value - Interface text by key, or a
   *   message from the local service as it is.
   */
  function announce(value) {
    setNotice(value);
    window.clearTimeout(noticeTimerRef.current);
    noticeTimerRef.current = window.setTimeout(() => setNotice(null), NOTICE_DURATION_MS);
  }

  /**
   * Say what just happened, in the interface language.
   * @param {string} key - The interface text.
   * @param {object} [values] - Values for its placeholders.
   */
  function showNotice(key, values = {}) {
    announce({ key, values });
  }

  /**
   * Say why something failed, in the local service's own words, or the interface's for a refusal it knows.
   * @param {Error} error - The failure.
   */
  function showError(error) {
    const key = refusalKey(error.message);
    announce(key ? { key } : { text: error.message });
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

  /** Load the Library's items, with their areas and goals, its connected folders and Open with's apps. */
  async function loadLibrary() {
    try {
      const knowledge = await api("/api/knowledge");
      setLibrary({ items: knowledge.sources, folders: knowledge.folders || [], openWith: knowledge.openWith || {},
        obsidian: Boolean(knowledge.obsidian), error: "" });
    } catch (error) {
      setLibrary({ items: null, folders: [], openWith: {}, obsidian: false, error: error.message });
    }
  }

  useEffect(() => {
    loadDay(today, false);
    loadCalendar(today.slice(0, 7));
  }, []);

  useEffect(() => {
    if (backendConnected) loadLibrary();
  }, [backendConnected]);

  /** Load today, or show the in-memory preview day when the local service is unreachable. */
  async function showToday() {
    setMonth(today.slice(0, 7));
    if (backendConnected) await loadDay(today, false);
    else setDay(previewTodayRef.current);
  }

  /**
   * Load one date, and its month when that differs from the month on show.
   * @param {string} date - The YYYY-MM-DD date to load.
   */
  async function showDate(date) {
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

  /**
   * Set one of the selected day's plans, or replace the plan already set once the user has reviewed
   * every change.
   * @param {string} variantId - The plan to set.
   * @param {boolean} replaceExisting - True only after the user approved replacing a set plan.
   * @returns {Promise<boolean>} True when the plan is now set.
   */
  async function setPlan(variantId, replaceExisting) {
    if (!backendConnected) {
      showNotice("noticeSetPlanNeedsService");
      return false;
    }
    try {
      await api("/api/plan/confirm", { method: "POST", body: JSON.stringify({ date: day.date, variantId, replaceExisting }) });
      await loadDay(day.date, false);
      await loadCalendar(month);
      showNotice(replaceExisting ? "noticePlanReplaced" : "noticePlanSet");
      return true;
    } catch (error) {
      showError(error);
      return false;
    }
  }

  async function updateEntry(entryId, status) {
    if (!backendConnected) {
      showNotice("noticeReportNeedsService");
      return;
    }
    if (backendConnected) {
      try {
        await api(`/api/entries/${entryId}`, { method: "PATCH", body: JSON.stringify({ status }) });
      } catch (error) {
        showError(error);
        return;
      }
    }
    await loadDay(day.date, false);
    await loadCalendar(month);
    showNotice("noticeMarked", { status });
  }

  async function discardAdvice(suggestionId) {
    try {
      const outcome = await api(`/api/suggestion-pool/${suggestionId}/discard`, { method: "POST" });
      await loadSummaries(day.date);
      showNotice("noticeAdviceDismissed", { count: outcome.affectedPeriods });
    } catch (error) { showError(error); }
  }

  /**
   * Delete a week's saved advice for one area, for good. The page asks for confirmation in two
   * steps before calling this; the local service still requires the confirmation phrase.
   * @param {string} week - The ISO week, such as 2026-W39.
   * @param {string} domain - The area whose advice is deleted.
   */
  async function clearAdviceWeek(week, domain) {
    try {
      const outcome = await api("/api/suggestion-pool/clear-week", {
        method: "POST", body: JSON.stringify({ week, domain, confirmation: `CLEAR ${week} ${domain.toUpperCase()}` }),
      });
      await loadSummaries(day.date);
      showNotice("noticeWeekCleared", { count: outcome.deletedAdvice });
    } catch (error) { showError(error); }
  }

  async function saveGoal(goalId, payload) {
    if (!backendConnected) return;
    try {
      await api(goalId ? `/api/goals/${goalId}` : "/api/goals", {
        method: goalId ? "PUT" : "POST", body: JSON.stringify(payload),
      });
      await loadDay(day.date, false);
      showNotice(goalId ? "noticeGoalUpdated" : "noticeGoalAdded");
    } catch (error) {
      showError(error);
      throw error;
    }
  }

  /**
   * Create or update a dated record, then reload the date it now belongs to.
   * @param {object} payload - The record fields the local service expects.
   * @param {string|null} itemId - The record to update, or null to create one.
   * @returns {Promise<boolean>} True when the record moved to a different date than the one on show.
   */
  async function saveItem(payload, itemId = null) {
    if (!backendConnected) return false;
    try {
      await api(itemId ? `/api/daily-items/${itemId}` : "/api/daily-items", {
        method: itemId ? "PUT" : "POST", body: JSON.stringify(payload),
      });
      await loadCalendar(month);
      const moved = payload.date !== day.date;
      if (moved) {
        await showDate(payload.date);
      } else {
        await loadDay(day.date, false);
      }
      showNotice(itemId ? "noticeTaskUpdated" : "noticeTaskAdded");
      return moved;
    } catch (error) {
      showError(error);
      throw error;
    }
  }

  async function updateItemStatus(item, status) {
    await saveItem({
      date: item.date, title: item.title, detail: item.detail, domain: item.domain,
      startTime: item.start_time, durationMinutes: item.duration_minutes,
      constraintKind: item.constraint_kind, repeatKind: item.repeatKind,
      goalId: item.goalId, status,
    }, item.id);
  }

  async function removeItem(item) {
    if (!backendConnected) return;
    try {
      await api(`/api/daily-items/${item.id}`, { method: "DELETE" });
      await loadCalendar(month);
      await loadDay(day.date, false);
      showNotice("noticeTaskRemoved");
    } catch (error) {
      showError(error);
      throw error;
    }
  }

  /**
   * Add an agent's suggestion to its day, or dismiss it. Until added, no plan uses it.
   * @param {object} item - The pending task the agent prepared.
   * @param {"accept"|"dismiss"} decision - What the user chose.
   */
  async function decideSuggestion(item, decision) {
    if (!backendConnected) return;
    try {
      await api(`/api/daily-items/${item.id}/${decision}`, { method: "POST" });
      await loadDay(day.date, false);
      await loadCalendar(month);
      showNotice(decision === "accept" ? "noticeSuggestionAdded" : "noticeSuggestionDismissed");
    } catch (error) {
      showError(error);
    }
  }

  async function removeGoal(goal) {
    if (!backendConnected) return;
    try {
      await api(`/api/goals/${goal.id}`, { method: "DELETE" });
      await loadDay(day.date, false);
      showNotice("noticeGoalRemoved");
    } catch (error) {
      showError(error);
      throw error;
    }
  }

  /**
   * Have the Orchestrator propose the selected day's plans, or propose again the ones not set. The
   * local model chooses among them, which can take a while, so `proposing` is true meanwhile.
   * @param {string} path - The service route that proposes.
   * @param {string} done - The notice key to show once the plans are ready.
   * @returns {Promise<boolean>} True when plans were proposed and are ready to review.
   */
  async function propose(path, done) {
    if (!backendConnected) {
      showNotice("noticeProposeNeedsService");
      return false;
    }
    setProposing(true);
    try {
      await api(path, { method: "POST", body: JSON.stringify({ date: day.date }) });
      await loadDay(day.date, false);
      await loadCalendar(month);
      showNotice(done);
      return true;
    } catch (error) {
      showError(error);
      return false;
    } finally {
      setProposing(false);
    }
  }

  /**
   * Ask the Orchestrator for alternatives from the selected day's records.
   * @returns {Promise<boolean>} True when alternatives were built and are ready to review.
   */
  function buildPlan() {
    return propose("/api/plan/generate", "noticePlansProposed");
  }

  /**
   * Propose again today's plans that aren't set, from its tasks as they are now; a set plan stays.
   * @returns {Promise<boolean>} True when the plans were proposed again.
   */
  function reproposePlans() {
    return propose("/api/plan/repropose", "noticePlansProposedAgain");
  }

  /**
   * Stop following the selected day's set plan. Its proposals stay to compare and set again, and its
   * tasks keep what was reported for them.
   * @returns {Promise<boolean>} True when the plan was deselected.
   */
  async function unsetPlan() {
    if (!backendConnected) return false;
    try {
      await api("/api/plan/unset", { method: "POST", body: JSON.stringify({ date: day.date }) });
      await loadDay(day.date, false);
      await loadCalendar(month);
      showNotice("noticePlanDeselected");
      return true;
    } catch (error) {
      showError(error);
      return false;
    }
  }

  /**
   * Refresh after Ava's reply, or after a change it proposed was confirmed.
   * @param {object|null} model - The local model's status, from a reply.
   * @param {string} [variantId] - The plan a confirmed change set.
   * @param {string} [changedDate] - The day a confirmed change to a task touched.
   * @param {string} [actionType] - The kind of change: `edit_item` and `remove_item` change a past task,
   *   `change_meal` moves a meal, `add_item` adds a task and `add_goal` starts a goal.
   */
  async function handleConversationUpdate(model, variantId, changedDate, actionType) {
    if (variantId) {
      await loadDay(day.date, false);
      await loadCalendar(month);
      showNotice("noticeProposalApplied");
      return;
    }
    if (changedDate) {
      await loadDay(changedDate, false);
      await loadCalendar(changedDate.slice(0, 7));
      showNotice({ edit_item: "noticeTaskUpdated", remove_item: "noticeTaskRemoved", change_meal: "noticeMealMoved",
        add_item: "noticeTaskAdded", add_goal: "noticeGoalAdded", set_energy: "noticeEnergySaved" }[actionType]
        || "noticeFutureTaskUpdated");
      return;
    }
    if (model) setDay((current) => ({ ...current, model }));
  }

  /**
   * Show the messages the agents sent through Ava as the service last returned them, with how many are unread.
   * @param {{notices: object[], unreadNotices: number}} result - From marking them read, or from a reply.
   */
  function showNotices({ notices, unreadNotices }) {
    setDay((current) => ({ ...current, notices, unreadNotices }));
  }

  /** Mark Ava's messages about issues read, as the user now sees them, so the dot on Ava's button clears. */
  async function readNotices() {
    try {
      showNotices(await api("/api/notices/read", { method: "POST" }));
    } catch (error) {
      showError(error);
    }
  }

  /**
   * Reload the Library, and the day that counts its notes and files, after the Library changes.
   * @param {string[]} [saved=[]] - The names of notes or files just saved, to say they were.
   */
  async function refreshKnowledge(saved = []) {
    await Promise.all([loadDay(day.date, false), loadLibrary()]);
    if (saved.length) showNotice("savedToLibrary", { names: saved });
  }

  /**
   * Reload the day and the Library after Learning tasks were made from a source, which may have joined
   * a goal, naming the tasks.
   * @param {{title: string}[]} tasks - The tasks made.
   */
  async function tasksMade(tasks) {
    await Promise.all([loadDay(day.date, false), loadLibrary()]);
    showNotice(tasks.length === 1 ? "madeOneTask" : "madeTasks", { count: tasks.length, names: tasks.map((task) => task.title) });
  }

  /**
   * Add a reading, out of 5, to today's energy; the day's average of every reading is what Ava, the
   * agents, the plans proposed from now on and Calendar take into account. Choosing the level
   * already shown adds nothing.
   * @param {number} level - From 1, low, to 5, high.
   */
  async function reportEnergy(level) {
    if (!backendConnected || level === latestReading(day.energyReadings)) return;
    try {
      await api(`/api/energy/${today}`, { method: "PUT", body: JSON.stringify({ level }) });
      await loadDay(today, false);
      await loadCalendar(today.slice(0, 7));
      showNotice("noticeEnergySaved");
    } catch (error) {
      showError(error);
    }
  }

  return {
    today, day, month, calendarDays, reports, pool, backendConnected, notice, library, proposing,
    showToday, showDate, chooseMonth, setPlan, updateEntry, discardAdvice, clearAdviceWeek, saveGoal, saveItem,
    updateItemStatus, removeItem, decideSuggestion, removeGoal, buildPlan, reproposePlans, unsetPlan, handleConversationUpdate,
    refreshKnowledge, tasksMade, reportEnergy, readNotices, showNotices,
  };
}
