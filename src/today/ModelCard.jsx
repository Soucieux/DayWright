import { useState } from "react";
import { useI18n } from "../i18n";
import { openSettings } from "../settings/models";
import { Icon } from "../ui/Icon";

/**
 * Says the local model can't run, what still works without it, and that nothing is sent elsewhere
 * instead. Open Settings shows the models folder and why each model isn't ready; Details lists which
 * local parts the service found.
 * @param {object} props
 * @param {object} props.model - The model status the local service reports.
 */
export function ModelCard({ model }) {
  const { t } = useI18n();
  const [details, setDetails] = useState(false);
  const parts = [
    ["modelPartRuntime", model.runtimeAvailable], ["modelPartChat", model.chatModelAvailable],
    ["modelPartSearch", model.embeddingModelAvailable], ["modelPartSpeech", model.voiceModelAvailable],
  ];

  return (
    <section className="dw-card dw-model-card" aria-labelledby="dw-model-title">
      <h2 id="dw-model-title" className="dw-heading dw-model-title"><span className="dw-dot dw-dot-off" aria-hidden="true" />{t("modelUnavailable")}</h2>
      <p className="dw-muted">{t("modelUnavailableBody")}</p>
      <p className="dw-ledger-line"><Icon name="shield" size={18} /><span>{t("noFallbackSent")}</span></p>
      {details && (
        <ul className="dw-model-parts">
          {parts.map(([key, found]) => (
            <li key={key}><Icon name={found ? "check" : "x"} size={16} /><span>{t(key)}</span><span className="dw-caption">{t(found ? "partFound" : "partMissing")}</span></li>
          ))}
        </ul>
      )}
      <div className="dw-actions">
        <button type="button" className="dw-button" onClick={openSettings}><Icon name="settings" size={18} />{t("openSettings")}</button>
        <button type="button" className="dw-button dw-button-quiet" aria-expanded={details} onClick={() => setDetails(!details)}>{t(details ? "hideAction" : "detailsAction")}</button>
      </div>
    </section>
  );
}
