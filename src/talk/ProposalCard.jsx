import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { planName } from "../plans/planName";
import { formatMinutes, fullDate } from "../time";
import { proposalView } from "./proposal";

/**
 * A change the agents proposed, pencilled until the user confirms or dismisses it. It lists exactly
 * what would change and what stays as it is; nothing is applied until Confirm.
 * @param {object} props
 * @param {object} props.proposal - The proposed change.
 * @param {object} props.day - The day on show, for its plans and tasks.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the change can be applied.
 * @param {(payload: object) => Promise<void>} props.onConfirmed - Refresh after the change is applied.
 */
export function ProposalCard({ proposal, day, today, backendConnected, onConfirmed }) {
  const { t, language, demoText } = useI18n();
  const [decision, setDecision] = useState("");
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
      await api(`/api/actions/${encodeURIComponent(proposal.id)}`, { method: "POST", body: JSON.stringify({ decision: choice }) });
      setDecision(choice);
      if (choice === "confirmed") await onConfirmed(proposal.payload);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  if (decision) {
    return <p className="dw-talk-decided" role="status" tabIndex={-1} ref={statusRef}><Icon name={decision === "confirmed" ? "check" : "x"} size={16} />{t(decision === "confirmed" ? "proposalConfirmed" : "proposalDismissed")}</p>;
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
