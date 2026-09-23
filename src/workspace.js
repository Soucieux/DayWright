import { useEffect, useMemo, useRef, useState } from "react";
import { api, getCalendar, getDay, getSummaries } from "./api";

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
    balance: { learning: 0, life: 0, finance: 0, rest: 0 },
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
 * month, Summary reports and the local service connection.
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
  const [notice, setNotice] = useState("");

  function showNotice(message) {
    setNotice(message);
    window.clearTimeout(noticeTimerRef.current);
    noticeTimerRef.current = window.setTimeout(() => setNotice(""), NOTICE_DURATION_MS);
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
    loadDay(today, false);
    loadCalendar(today.slice(0, 7));
  }, []);

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
      showNotice("Start the local service to save a plan confirmation.");
      return false;
    }
    try {
      await api("/api/plan/confirm", { method: "POST", body: JSON.stringify({ date: day.date, variantId, replaceExisting }) });
      await loadDay(day.date, false);
      await loadCalendar(month);
      showNotice(replaceExisting ? "Confirmed plan replaced for this date." : "Day confirmed. Calendar and area ledgers are updated.");
      return true;
    } catch (error) {
      showNotice(error.message);
      return false;
    }
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

  async function discardAdvice(suggestionId) {
    try {
      const outcome = await api(`/api/suggestion-pool/${suggestionId}/discard`, { method: "POST" });
      await loadSummaries(day.date);
      showNotice(`Advice discarded across ${outcome.affectedPeriods} period${outcome.affectedPeriods === 1 ? "" : "s"}.`);
    } catch (error) { showNotice(error.message); }
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
      showNotice(itemId ? "Daily item updated." : "Daily item recorded. It now appears in Calendar and its area.");
      return moved;
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

  async function removeItem(item) {
    if (!backendConnected) return;
    try {
      await api(`/api/daily-items/${item.id}`, { method: "DELETE" });
      await loadCalendar(month);
      await loadDay(day.date, false);
      showNotice("Daily item removed. Confirmed days keep their own record.");
    } catch (error) {
      showNotice(error.message);
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
      showNotice(decision === "accept" ? "Suggestion added to its day." : "Suggestion dismissed; it won't be suggested again for that day.");
    } catch (error) {
      showNotice(error.message);
    }
  }

  async function removeGoal(goal) {
    if (!backendConnected) return;
    try {
      await api(`/api/goals/${goal.id}`, { method: "DELETE" });
      await loadDay(day.date, false);
      showNotice("Goal removed.");
    } catch (error) {
      showNotice(error.message);
      throw error;
    }
  }

  /**
   * Ask the Orchestrator for alternatives from the selected day's records.
   * @returns {Promise<boolean>} True when alternatives were built and are ready to review.
   */
  async function buildPlan() {
    if (!backendConnected) {
      showNotice("Start the local service to build a saved plan.");
      return false;
    }
    try {
      await api("/api/plan/generate", { method: "POST", body: JSON.stringify({ date: day.date }) });
      await loadDay(day.date, false);
      await loadCalendar(month);
      showNotice("Built a plan from your dated items. Review it before confirming.");
      return true;
    } catch (error) {
      showNotice(error.message);
      return false;
    }
  }

  async function handleConversationUpdate(model, variantId, changedDate) {
    if (variantId) {
      await loadDay(day.date, false);
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
    if (model) setDay((current) => ({ ...current, model }));
  }

  async function handleKnowledgeSaved(source) {
    await loadDay(day.date, false);
    showNotice(`Indexed ${source.chunkCount} ${source.sourceUrl ? "attributed public" : "private"} chunk${source.chunkCount === 1 ? "" : "s"}.`);
  }

  async function handleAreaSaved() {
    await loadDay(day.date, false);
    await loadCalendar(month);
  }

  return {
    today, day, month, calendarDays, reports, pool, backendConnected, notice,
    showToday, showDate, chooseMonth, setPlan, updateEntry, discardAdvice, clearAdviceWeek, saveGoal, saveItem,
    updateItemStatus, removeItem, decideSuggestion, removeGoal, buildPlan, handleConversationUpdate,
    handleKnowledgeSaved, handleAreaSaved,
  };
}
