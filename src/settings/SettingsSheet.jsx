import { useCallback, useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Sheet } from "../ui/Sheet";
import { modelStateText, runnerText } from "./models";

/** What each model runs, by its role. */
const MODEL_USES = { chat: "modelForChat", embedding: "modelForEmbedding", speech: "modelForSpeech" };
/** How often Settings reads the states again while a checksum is being taken, in milliseconds. */
const CHECKING_POLL_MS = 1500;

/**
 * A model's or the runner's state at the row's end: a mark and its words, Ready only when it is.
 * @param {object} props
 * @param {boolean} props.ok - Whether it is ready, or found.
 * @param {boolean} [props.checking=false] - Whether its checksum is being taken.
 * @param {string} props.children - Its words.
 */
function State({ ok, checking = false, children }) {
  return (
    <span className={`dw-model-state${ok ? " is-ready" : checking ? " is-checking" : " is-missing"}`}>
      <Icon name={ok ? "check" : checking ? "clock" : "alert"} size={16} />{children}
    </span>
  );
}

/**
 * Settings, opened from the app menu's Settings… (⌘,), the gear beside the Guide, or any Open Settings. Its first
 * section is Models: the one folder every model is read from, chosen in the Mac's own window or typed, or none;
 * each model's state, naming the exact place looked in; and the runner, found or not, which is shown, not chosen.
 * Nothing in the folder is ever written; Stop using this folder forgets the choice.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {() => void} props.onChanged - Read the day again, as a folder chosen or stopped changes what works.
 * @param {() => void} props.onClose - Close Settings.
 */
export function SettingsSheet({ backendConnected, onChanged, onClose }) {
  const { t } = useI18n();
  const fieldId = useId();
  const [models, setModels] = useState(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setModels(await api("/api/models"));
    } catch (caught) {
      setError(caught.message);
    }
  }, []);

  useEffect(() => {
    if (backendConnected) load();
  }, [backendConnected, load]);

  // While a checksum is being taken the row reads Checking…, never Ready, until it is done; then the day is read
  // again, so what that model runs works without waiting for another change.
  const checking = Boolean(models?.models.some((model) => model.state === "checking"));
  const wasChecking = useRef(false);
  useEffect(() => {
    if (wasChecking.current && !checking) onChanged();
    wasChecking.current = checking;
    if (!checking) return undefined;
    const timer = window.setTimeout(load, CHECKING_POLL_MS);
    return () => window.clearTimeout(timer);
  }, [checking, models, load, onChanged]);

  /** Choose or stop using a folder, then show the states it leaves and read the day again. */
  async function change(request) {
    setBusy(true);
    setError("");
    try {
      setModels(await request());
      onChanged();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  const use = (path) => change(() => api("/api/models/folder", { method: "POST", body: JSON.stringify({ path }) }));

  async function pick() {
    setBusy(true);
    setError("");
    try {
      const answer = await api("/api/models/folder/choose", { method: "POST" });
      if (answer.path) await use(answer.path);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet title={t("settingsTitle")} onClose={onClose}>
      <section className="dw-settings-section" aria-labelledby="dw-settings-models">
        <h3 id="dw-settings-models" className="dw-section-label">{t("settingsModels")}</h3>
        <p className="dw-muted">{t("modelsLead")}</p>
        {!backendConnected ? <p className="dw-muted">{t("settingsServiceOff")}</p> : models && (
          <>
            <div className="dw-settings-folder">
              <span className="dw-field-label">{t("modelsFolderLabel")}</span>
              {models.state === "none" ? (
                <><p className="dw-settings-path">{t("modelsNoFolder")}</p><p className="dw-caption">{t("modelsNoFolderBody")}</p></>
              ) : models.state === "notFound" ? (
                <><State ok={false}>{t("modelsFolderNotFound", { path: models.folder })}</State>
                  <p className="dw-caption">{t("modelsFolderNotFoundBody")}</p></>
              ) : <p className="dw-settings-path">{models.folder}</p>}
              <div className="dw-actions">
                <button type="button" className="dw-button" disabled={busy} onClick={pick}>
                  <Icon name="folder" size={18} />{t(models.folder ? "modelsChooseAnother" : "modelsChooseFolder")}</button>
                {models.folder && (
                  <button type="button" className="dw-button dw-button-quiet" disabled={busy}
                    onClick={() => change(() => api("/api/models/folder", { method: "DELETE" }))}>{t("modelsStopUsing")}</button>
                )}
              </div>
              {models.folder && <p className="dw-caption">{t("modelsStopNote")}</p>}
              <form className="dw-field dw-settings-typed" onSubmit={(event) => { event.preventDefault(); if (typed.trim()) use(typed.trim()); }}>
                <label className="dw-field-label" htmlFor={fieldId}>{t("folderPathLabel")}</label>
                <div className="dw-settings-typed-row">
                  <input id={fieldId} type="text" spellCheck={false} autoComplete="off" maxLength={4096} value={typed}
                    onChange={(event) => setTyped(event.target.value)} />
                  <button type="submit" className="dw-button" disabled={busy || !typed.trim()}>{t("modelsUseTyped")}</button>
                </div>
              </form>
            </div>
            <ul className="dw-settings-models">
              {models.models.map((model) => (
                <li key={model.role}>
                  <span className="dw-settings-model"><span className="dw-settings-name">{model.name}</span>
                    <span className="dw-caption">{t(MODEL_USES[model.role])}</span></span>
                  <State ok={model.state === "ready"} checking={model.state === "checking"}>{modelStateText(model, models, t)}</State>
                </li>
              ))}
              {models.runner && (
                <li>
                  <span className="dw-settings-model"><span className="dw-settings-name">{t("runnerLabel")} · llama-server</span>
                    <span className="dw-caption">{t("runnerFor")}</span></span>
                  <State ok={models.runner.state === "found"}>{runnerText(models.runner, t)}</State>
                  <p className="dw-caption dw-settings-note">{t(models.runner.state === "found" ? "runnerNote" : "runnerMissingNote")}</p>
                </li>
              )}
            </ul>
            <button type="button" className="dw-button dw-button-quiet" disabled={busy} onClick={load}>
              <Icon name="repeat" size={18} />{t("checkAgainAction")}</button>
          </>
        )}
        {error && <p className="dw-alert" role="alert">{error}</p>}
      </section>
    </Sheet>
  );
}
