import { useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";

/**
 * Says the local model can't run, what still works without it, and that nothing is sent elsewhere
 * instead. Try again asks the local service to start it; Details lists which local parts it found.
 * @param {object} props
 * @param {object} props.model - The model status the local service reports.
 * @param {(model: object) => void} props.onModel - Take a fresh model status.
 */
export function ModelCard({ model, onModel }) {
  const { t } = useI18n();
  const [checking, setChecking] = useState(false);
  const [details, setDetails] = useState(false);
  const [error, setError] = useState("");
  const parts = [
    ["modelPartRuntime", model.runtimeAvailable], ["modelPartChat", model.chatModelAvailable],
    ["modelPartSearch", model.embeddingModelAvailable], ["modelPartSpeech", model.voiceModelAvailable],
  ];

  async function retry() {
    setChecking(true);
    setError("");
    try {
      onModel(await api("/api/model/start", { method: "POST" }));
    } catch (caught) {
      setError(caught.message);
    } finally {
      setChecking(false);
    }
  }

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
      {error && <p className="dw-alert" role="alert">{error}</p>}
      <div className="dw-actions">
        <button type="button" className="dw-button" disabled={checking} onClick={retry}><Icon name="repeat" size={18} />{checking ? t("modelChecking") : t("tryAgainAction")}</button>
        <button type="button" className="dw-button dw-button-quiet" aria-expanded={details} onClick={() => setDetails(!details)}>{t(details ? "hideAction" : "detailsAction")}</button>
      </div>
    </section>
  );
}
