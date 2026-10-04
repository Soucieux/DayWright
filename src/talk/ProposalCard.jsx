import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { planName } from "../plans/planName";
import { formatMinutes, fullDate } from "../time";
import { changeLine, proposalView } from "./proposal";

/** The icon beside each change an edit makes to a past task. */
const CHANGE_ICONS = {
  title: "pencil", detail: "pencil", domain: "target", goalId: "link", date: "calendar",
  startTime: "clock", durationMinutes: "clock", status: "check",
};

/**
 * What a confirmed meal move did to today's set plan: the tasks fitted around the meal, or, when
 * the plan is up for review, the new plans to pick from here, or to compare in Plans.
 * @param {object} props
 * @param {{planUpdate: string, changes: object[], review?: {options: object[]}}} props.outcome - The move's result.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether a plan can be set.
 * @param {(option: object) => Promise<void>} props.onPicked - Refresh after one of the new plans is set.
 * @param {() => void} props.onOpenPlans - Show today's plans.
 */
function MealOutcome({ outcome, today, backendConnected, onPicked, onOpenPlans }) {
  const { t, demoText } = useI18n();
  const [picked, setPicked] = useState(null);
  const [error, setError] = useState("");

  /**
   * Set one of the new plans in place of today's set plan.
   * @param {{id: string, name: string, slug: string}} option - The plan picked.
   */
  async function use(option) {
    setError("");
    try {
      await api("/api/plan/confirm", { method: "POST", body: JSON.stringify({ date: today, variantId: option.id, replaceExisting: true }) });
      setPicked(option);
      await onPicked(option);
    } catch (caught) {
      setError(caught.message);
    }
  }

  if (outcome.planUpdate === "adjusted") {
    return (
      <>
        <p className="dw-caption">{t("mealAdjustedTitle")}</p>
        <ul className="dw-proposal-changes">
          {outcome.changes.map((change) => (
            <li key={change.title}><Icon name="clock" size={18} /><span>{t("proposalMoveLine", { title: demoText(change.title), from: change.from, to: change.to })}</span></li>
          ))}
        </ul>
      </>
    );
  }
  if (outcome.planUpdate !== "review") return null;
  if (picked) return <p className="dw-caption" role="status">{t("mealReviewSet", { name: planName(picked, t, demoText) })}</p>;
  return (
    <>
      <p className="dw-caption">{t("mealReviewTitle")}</p>
      <div className="dw-actions">
        {outcome.review.options.map((option) => (
          <button key={option.id} type="button" className="dw-button" disabled={!backendConnected} onClick={() => use(option)}>
            {t("mealReviewUse", { name: planName(option, t, demoText) })}</button>
        ))}
        <button type="button" className="dw-button dw-button-quiet" onClick={onOpenPlans}>{t("mealReviewCompare")}</button>
      </div>
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </>
  );
}

/**
 * A change the agents proposed, pencilled until the user confirms or dismisses it. It lists exactly
 * what would change and what stays as it is; nothing is applied until Confirm.
 * @param {object} props
 * @param {object} props.proposal - The proposed change.
 * @param {object} props.day - The day on show, for its plans and tasks.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the change can be applied.
 * @param {(payload: object, actionType: string) => Promise<void>} props.onConfirmed - Refresh after the
 *   change is applied, given what it changed and its kind.
 * @param {() => void} props.onOpenPlans - Show today's plans, to compare them after a meal move.
 */
export function ProposalCard({ proposal, day, today, backendConnected, onConfirmed, onOpenPlans }) {
  const { t, language, demoText } = useI18n();
  const [decision, setDecision] = useState("");
  const [outcome, setOutcome] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const statusRef = useRef(null);
  const view = proposalView(proposal, day.dayItems || []);
  const when = view.date === today ? t("todayWord") : view.date ? fullDate(view.date, language) : "";
  const plan = (id, name) => planName((day.variants || []).find((variant) => variant.id === id), t, demoText) || demoText(name);

  const [title, changes] = view.kind === "set" ? [t("proposalSetTitle", { date: when }), [
    ["check", t("proposalSetLine", { name: plan(proposal.payload.variantId, view.to) })],
    ["target", t("goalsOnlyOnReport")],
  ]] : view.kind === "replace" ? [t("proposalReplaceTitle", { date: when }), [
    ["repeat", t("proposalReplaceLine", { from: plan(proposal.payload.reviewedFromVariantId, view.from), to: plan(proposal.payload.variantId, view.to) })],
    ["lock", t("reportedKeepStatus")],
    ["target", t("goalsOnlyOnReport")],
  ]] : view.kind === "shorten" ? [t("proposalShortenTitle", { date: when }), [
    ["clock", view.title
      ? t("proposalShortenLine", { title: demoText(view.title), from: formatMinutes(view.from, language), to: formatMinutes(view.to, language) })
      : t("proposalShortenTo", { to: formatMinutes(view.to, language) })],
    ["calendar", t("proposalStaysOnCalendar")],
  ]] : view.kind === "move" ? [t("proposalMoveTitle", { date: when }), [
    ["clock", view.title
      ? t("proposalMoveLine", { title: demoText(view.title), from: view.from || t("noStartTime"), to: view.to })
      : t("proposalMoveTo", { to: view.to })],
    ["pin", t("proposalMoveFixed")],
  ]] : view.kind === "length" ? [t("proposalShortenTitle", { date: when }), [
    ["clock", view.title
      ? t("proposalShortenLine", { title: `“${demoText(view.title)}”`, from: formatMinutes(view.from, language), to: formatMinutes(view.to, language) })
      : t("proposalLengthTo", { to: formatMinutes(view.to, language) })],
    ["shield", t("proposalLengthYours")],
  ]] : view.kind === "edit" ? [t("proposalEditTitle", { title: demoText(view.title), date: when }), [
    ...view.changes.map((change) => [CHANGE_ICONS[change.field], changeLine(change, t, language, day.goals || [], demoText)]),
    ["lock", t("proposalEditNote")],
  ]] : view.kind === "meal" ? [t(view.scope === "standing" ? "proposalMealStandingTitle" : "proposalMealDayTitle",
    { meal: t(`meal${view.title}`), date: when }), [
    ["meal", t("proposalMealLine", { meal: t(`mealName${view.title}`), from: view.from, to: view.to })],
    ["calendar", t(view.planChanges ? "proposalMealPlanChanges" : "proposalMealKeepsFree")],
  ]] : view.kind === "remove" ? [t("proposalRemoveTitle", { date: when }), [
    ["trash", t("proposalRemoveLine", { title: demoText(view.title), when: view.start || t("noStartTime"),
      length: formatMinutes(view.minutes, language) })],
    ...(view.keptByPlan ? [["calendar", t("proposalRemoveKeptEntry")]] : []),
    ["lock", t("proposalRemoveNote")],
  ]] : [t("proposalOtherTitle"), [["info", demoText(proposal.explanation)]]];

  // The button that decided is gone once the card becomes its outcome; keep focus on that outcome.
  useEffect(() => {
    if (decision) statusRef.current?.focus();
  }, [decision]);

  /**
   * Confirm or dismiss the proposal. Only a confirmation changes anything.
   * @param {string} choice - `confirmed` or `dismissed`.
   */
  async function decide(choice) {
    setBusy(true);
    setError("");
    try {
      const decided = await api(`/api/actions/${encodeURIComponent(proposal.id)}`, { method: "POST", body: JSON.stringify({ decision: choice }) });
      setOutcome(decided);
      setDecision(choice);
      if (choice === "confirmed") await onConfirmed(proposal.payload, proposal.actionType);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  if (decision) {
    const status = <p className="dw-talk-decided" role="status" tabIndex={-1} ref={statusRef}><Icon name={decision === "confirmed" ? "check" : "x"} size={16} />{t(decision === "confirmed" ? "proposalConfirmed" : "proposalDismissed")}</p>;
    if (decision !== "confirmed" || !outcome?.planUpdate) return status;
    return (
      <div className="dw-meal-outcome">
        {status}
        <MealOutcome outcome={outcome} today={today} backendConnected={backendConnected} onOpenPlans={onOpenPlans}
          onPicked={(option) => onConfirmed({ date: today, variantId: option.id }, "select_variant")} />
      </div>
    );
  }
  return (
    <section className="dw-card dw-pencilled dw-proposal" aria-labelledby={`dw-proposal-${proposal.id}`}>
      <span className="dw-chip dw-chip-small dw-chip-dashed"><Icon name="pencil" size={14} />{t("proposedNotApplied")}</span>
      <h4 id={`dw-proposal-${proposal.id}`} className="dw-heading">{title}</h4>
      <ul className="dw-proposal-changes">
        {changes.map(([icon, line]) => <li key={line}><Icon name={icon} size={18} /><span>{line}</span></li>)}
      </ul>
      <p className="dw-caption">{t("nothingChangedYet")}</p>
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <div className="dw-actions">
        <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected || busy} onClick={() => decide("confirmed")}><Icon name="check" size={18} />{t("confirmChange")}</button>
        <button type="button" className="dw-button" disabled={!backendConnected || busy} onClick={() => decide("dismissed")}>{t("dismissAction")}</button>
      </div>
    </section>
  );
}
