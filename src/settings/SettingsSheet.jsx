import { useCallback, useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { FOLDER_PATH_CHARACTERS } from "../fieldLimits";
import { useI18n } from "../i18n";
import { ActionMenu } from "../ui/ActionMenu";
import { CentredSheet } from "../ui/CentredSheet";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { TabList } from "../ui/TabList";
import { DemoSection } from "./DemoSection";
import { MemorySection } from "./MemorySection";
import { ScheduleSection } from "./ScheduleSection";
import { deviceText, modelStateText } from "./models";
import { PANES, middleCut, modelPill, runnerPill } from "./panes";

/** Each model's row title, by its role: what it is and what it runs. */
const MODEL_ROLES = { chat: "modelRoleChat", embedding: "modelRoleEmbedding", speech: "modelRoleSpeech" };
/** How often Settings reads the states again while a checksum is being taken, in milliseconds. */
const CHECKING_POLL_MS = 1500;

/**
 * A state at a row's end, as a pill: its tone's colours, its icon and its words, so colour is never the only sign.
 * @param {object} props
 * @param {"success"|"neutral"|"warning"|"danger"} props.tone - Its colours.
 * @param {string} props.icon - Its icon.
 * @param {string} [props.label] - Its words' key, when `text` isn't given.
 * @param {string} [props.text] - Its words.
 */
export function StatusPill({ tone, icon, label, text }) {
  const { t } = useI18n();
  return <span className={`dw-status-pill is-${tone}`}><Icon name={icon} size={14} />{text ?? t(label)}</span>;
}

/**
 * Settings, centred over the page, opened from the app menu's Settings… (⌘,), the menu bar's Settings…, the gear
 * beside the Guide, or any Open Settings. Its header is a Mac settings toolbar: the pane on show named above four
 * panes, each an icon over its name, the chosen one tinted. Models: the one folder every model is read from, chosen in
 * the Mac's own window or typed, or none; each model's state, naming the exact place looked in while it isn't ready;
 * and the runner, llama-server, chosen the same way, or none, found or not. Nothing in the folder or beside the runner
 * is ever written; Stop using forgets a choice, which, like the language, holds for the demo too. Memory: what Ava
 * remembers (see MemorySection). Schedule: the work schedule and statutory holidays (see ScheduleSection). Demo:
 * opens, leaves and resets the demo workspace (see DemoSection).
 * @param {object} props
 * @param {"models"|"memory"|"schedule"|"demo"} [props.tab="models"] - The pane it opens on.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the demo is open.
 * @param {() => void} props.onChanged - Read the day again, as a folder or runner chosen or stopped changes what works.
 * @param {() => void} props.onClose - Close Settings.
 */
export function SettingsSheet({ tab = "models", backendConnected, demoMode, onChanged, onClose }) {
  const { t } = useI18n();
  const fieldId = useId();
  const [shown, setShown] = useState(tab);
  const [models, setModels] = useState(null);
  const [typing, setTyping] = useState(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  /** Load the models' states; a failure stays on show. */
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

  /** Choose or stop using a folder or runner, then show the states it leaves and read the day again. */
  async function change(request) {
    setBusy(true);
    setError("");
    try {
      setModels(await request());
      setTyping(null);
      onChanged();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  /** Use the models folder at `path`. */
  const use = (path) => change(() => api("/api/models/folder", { method: "POST", body: JSON.stringify({ path }) }));
  /** Run the chat and search models with the runner at `path`. */
  const useRunner = (path) => change(() => api("/api/models/runner", { method: "POST", body: JSON.stringify({ path }) }));
  /** Run models on: the model servers running stop, so each model's next use starts where it is now to run. */
  const chooseRunOn = (runOn) => runOn !== models.runOn
    && change(() => api("/api/models/run-on", { method: "PUT", body: JSON.stringify({ runOn }) }));

  /**
   * Choose in the Mac's own window and use what was chosen; choosing none changes nothing.
   * @param {() => Promise<{path: string|null}>} request - Ask the service to open the Mac's window.
   * @param {(path: string) => Promise<void>} using - Use the path chosen.
   */
  async function pick(request, using) {
    setBusy(true);
    setError("");
    try {
      const answer = await request();
      if (answer.path) await using(answer.path);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setBusy(false);
    }
  }

  /** Choose the models folder in the Mac's own window. */
  const pickFolder = () => pick(() => api("/api/models/folder/choose", { method: "POST" }), use);
  /** Choose the runner in the Mac's own window. */
  const pickRunner = () => pick(() => api("/api/models/runner/choose", { method: "POST" }), useRunner);

  /**
   * Do what a ⋯ menu names: show the field a path is typed in, or stop using the folder or the runner.
   * @param {"folder"|"runner"} target - Whose menu it is.
   * @param {"type"|"stop"} value - The item chosen.
   */
  function onMore(target, value) {
    if (value === "type") setTyping(target);
    else if (target === "folder") change(() => api("/api/models/folder", { method: "DELETE" }));
    else change(() => api("/api/models/runner", { method: "DELETE" }));
  }

  // The field a path is typed in, under the row whose menu asked for it.
  const typedPath = typing && (
    <form className="dw-field dw-settings-typed" onSubmit={(event) => {
      event.preventDefault();
      if (typed.trim()) (typing === "runner" ? useRunner : use)(typed.trim());
    }}>
      <label className="dw-field-label" htmlFor={fieldId}>{t("folderPathLabel")}</label>
      <div className="dw-settings-typed-row">
        <input id={fieldId} type="text" spellCheck={false} autoComplete="off" maxLength={FOLDER_PATH_CHARACTERS} value={typed} autoFocus
          onChange={(event) => setTyped(event.target.value)} />
        <button type="submit" className="dw-button" disabled={busy || !typed.trim()}>
          {t(typing === "runner" ? "runnerUseTyped" : "modelsUseTyped")}</button>
      </div>
    </form>
  );

  const paneKey = PANES.find(([id]) => id === shown)[1];
  const toolbar = (
    <TabList label={t("settingsTitle")} idBase="dw-settings" className="dw-panes" tabClassName="dw-pane" selected={shown}
      onSelect={setShown} tabs={PANES.map(([id, key, icon]) => [id, <><Icon name={icon} size={22} /><span>{t(key)}</span></>])} />
  );

  return (
    <CentredSheet title={t(paneKey)} name={t("settingsTitle")} wide toolbar={toolbar} onClose={onClose}>
      <div id="dw-settings-panel" className="dw-settings-panel" role="tabpanel" aria-labelledby={`dw-settings-tab-${shown}`}>
        {shown === "models" && <section className="dw-settings-section">
          {!backendConnected ? <p className="dw-set-lead">{t("settingsServiceOff")}</p> : <p className="dw-set-lead">{t("modelsLead")}</p>}
          {backendConnected && models && (
            <>
              <ul className="dw-set-list">
                <li className="dw-set-row">
                  <span className="dw-set-row-icon"><Icon name="folder" size={20} /></span>
                  <span className="dw-set-row-main">
                    <span className="dw-set-title">{t("modelsFolderLabel")}</span>
                    {models.state === "none" ? <span className="dw-set-caption">{t("modelsNoFolderShort")}</span> : (
                      <span className="dw-set-path" tabIndex={0} title={models.folder}>
                        <span className="dw-set-path-cut" aria-hidden="true">{middleCut(models.folder)}</span>
                        <span className="dw-set-path-whole">{models.folder}</span>
                      </span>
                    )}
                  </span>
                  <span className="dw-set-row-end">
                    {models.state === "notFound" && <StatusPill tone="warning" icon="alert" text={t("pillCantFind")} />}
                    {models.state === "none" ? (
                      <button type="button" className="dw-button dw-button-primary" disabled={busy} onClick={pickFolder}>
                        {t("modelsChooseFolder")}</button>
                    ) : (
                      <button type="button" className="dw-button" disabled={busy} onClick={pickFolder}>{t("modelsChange")}</button>
                    )}
                    <ActionMenu icon="more" label={t("modelsMore")} items={[
                      { value: "type", label: t("modelsTypePath") },
                      ...(models.folder ? [{ value: "stop", label: t("modelsStopUsing"), note: t("modelsStopNote") }] : []),
                    ]} disabled={busy} onChoose={(value) => onMore("folder", value)} />
                  </span>
                  {models.state !== "found" && (
                    <p className="dw-set-caption dw-set-row-note">
                      {t(models.state === "none" ? "modelsNoFolderBody" : "modelsFolderNotFoundBody")}</p>
                  )}
                </li>
                <li className="dw-set-row">
                  <span className="dw-set-row-icon"><Icon name="chip" size={20} /></span>
                  <span className="dw-set-row-main">
                    <span className="dw-set-title">{t("runModelsOn")}</span>
                    <span className="dw-set-caption">{t("runModelsOnNote")}</span>
                  </span>
                  <span className="dw-set-row-end">
                    <Segmented label={t("runModelsOn")} value={models.runOn} onChange={chooseRunOn}
                      options={[["automatic", t("runOnAutomatic")], ["processor", t("runOnProcessor")]]} />
                  </span>
                </li>
              </ul>
              {typing === "folder" && typedPath}
              <div className="dw-set-group">
                <div className="dw-set-head"><h3 className="dw-set-heading">{t("settingsModels")}</h3>
                  <button type="button" className="dw-button dw-button-quiet dw-set-head-action" disabled={busy} onClick={load}>
                    <Icon name="repeat" size={16} />{t("checkAgainAction")}</button></div>
                <ul className="dw-set-list">
                  {models.models.map((model) => (
                    <li key={model.role} className="dw-set-row">
                      <span className="dw-set-row-main">
                        <span className="dw-set-title">{t(MODEL_ROLES[model.role])}</span>
                        <span className="dw-set-caption">
                          {model.state === "ready" || model.state === "checking" ? model.name : modelStateText(model, models, t)}</span>
                        {model.state === "ready" && models.devices?.[model.role] && (
                          <span className="dw-set-caption dw-set-device">{deviceText(models.devices[model.role], t)}</span>
                        )}
                      </span>
                      <span className="dw-set-row-end"><StatusPill {...modelPill(model.state)} /></span>
                    </li>
                  ))}
                  <li className="dw-set-row">
                    <span className="dw-set-row-main">
                      <span className="dw-set-title">{t("runnerLabel")}</span>
                      <span className="dw-set-caption">{models.runner.location
                        ? `${models.runner.location.split("/").pop()} · ${models.runner.location}` : t("runnerNoneShort")}</span>
                      {models.runner.state !== "found" && (
                        <span className="dw-set-caption">{t(models.runner.state === "none" ? "runnerNoneBody" : "runnerMissingNote")}</span>
                      )}
                    </span>
                    <span className="dw-set-row-end">
                      <StatusPill {...runnerPill(models.runner.state)} />
                      <button type="button" className={models.runner.state === "none" ? "dw-button dw-button-primary" : "dw-button"}
                        disabled={busy} onClick={pickRunner}>{t(models.runner.state === "none" ? "runnerChoose" : "modelsChange")}</button>
                      <ActionMenu icon="more" label={t("runnerMore")} items={[
                        { value: "type", label: t("modelsTypePath") },
                        ...(models.runner.location ? [{ value: "stop", label: t("runnerStopUsing"), note: t("runnerStopNote") }] : []),
                      ]} disabled={busy} onChoose={(value) => onMore("runner", value)} />
                    </span>
                  </li>
                </ul>
                {typing === "runner" && typedPath}
              </div>
            </>
          )}
          {error && <p className="dw-alert" role="alert">{error}</p>}
        </section>}
        {shown === "memory" && <MemorySection backendConnected={backendConnected} onChanged={onChanged} />}
        {shown === "schedule" && <ScheduleSection backendConnected={backendConnected} onChanged={onChanged} />}
        {shown === "demo" && <DemoSection backendConnected={backendConnected} demoMode={demoMode} />}
      </div>
    </CentredSheet>
  );
}
