import { useState } from "react";
import { useI18n } from "../i18n";
import { AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { formatMinutes, longDate } from "../time";

/**
 * An agent's suggestion for a day, pencilled until the user decides: what, when, the evidence
 * behind it, and Add or Dismiss. No plan uses it before it is added.
 * @param {object} props
 * @param {object} props.item - The pending task the agent prepared.
 * @param {boolean} props.backendConnected - Whether a decision can be saved.
 * @param {(item: object, decision: "accept"|"dismiss") => Promise<void>} props.onDecide - Add or dismiss it.
 */
export function SuggestionCard({ item, backendConnected, onDecide }) {
  const { t, language, demoText } = useI18n();
  const [busy, setBusy] = useState(false);
  const { weekday } = longDate(item.date, language);

  async function decide(decision) {
    setBusy(true);
    try {
      await onDecide(item, decision);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="dw-card dw-pencilled dw-suggestion" aria-labelledby={`dw-suggestion-${item.id}`}>
      <p className="dw-agent-line"><span className="dw-agent-mark"><Icon name="agent" size={16} /></span>
        <strong>{t("summaryAgent")}</strong><span className="dw-caption">· {t("suggestionLabel")}</span></p>
      <p id={`dw-suggestion-${item.id}`} className="dw-suggestion-title">
        <span className="dw-plan-time">{item.start_time}</span><AreaTag domain={item.domain} /><span>{demoText(item.title)}</span>
      </p>
      <p className="dw-caption">{formatMinutes(item.duration_minutes, language)}</p>
      <p className="dw-evidence"><Icon name="info" size={16} /><span><strong>{t("evidenceLabel")}</strong> {demoText(item.originDetail)}</span></p>
      <div className="dw-actions">
        <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected || busy} onClick={() => decide("accept")}>
          <Icon name="check" size={18} />{t("addToDay", { day: weekday })}
        </button>
        <button type="button" className="dw-button" disabled={!backendConnected || busy} onClick={() => decide("dismiss")}>{t("dismissAction")}</button>
      </div>
      <p className="dw-caption dw-suggestion-note">{backendConnected ? t("suggestionWaits") : t("previewCannotSave")}</p>
    </article>
  );
}
