import { useContext, useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { shortDay } from "./memory";
import { demoState } from "./panes";
import { WorkspaceSwitchContext } from "./useWorkspaceSwitch";

/**
 * Settings › Demo: two months of made-up use in a workspace of its own, as one card saying whether it is open, made
 * and kept, or not made yet; opened here and left here or from its banner, through the window's one switch (see
 * useWorkspaceSwitch), whose overlay says what is happening; every button here is off while it does. Reset asks
 * first, then deletes the demo and makes it anew, ending today; whatever was done in it until then is gone, and the
 * user's own data is never touched.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the demo is open.
 */
export function DemoSection({ backendConnected, demoMode }) {
  const { t, language } = useI18n();
  const { switching, start } = useContext(WorkspaceSwitchContext);
  const [asking, setAsking] = useState(false);
  const [madeOn, setMadeOn] = useState(null);
  const busy = Boolean(switching);

  useEffect(() => {
    if (!backendConnected) return;
    api("/api/health").then((health) => setMadeOn(health.demoMadeOn ?? null)).catch(() => setMadeOn(null));
  }, [backendConnected]);

  const state = demoState(demoMode, madeOn);
  const stateLine = t(state.key, state.values.date ? { date: shortDay(state.values.date, language) } : {});

  return (
    <section className="dw-settings-section">
      {!backendConnected ? <p className="dw-set-lead">{t("settingsServiceOff")}</p> : <p className="dw-set-lead">{t("demoLead")}</p>}
      {backendConnected && (asking ? (
        <div className="dw-confirm-remove" role="alertdialog" aria-labelledby="dw-demo-reset-title" aria-describedby="dw-demo-reset-body">
          <h3 id="dw-demo-reset-title">{t("demoResetQuestion")}</h3>
          <p id="dw-demo-reset-body">{t("demoResetBody")}</p>
          <div className="dw-actions">
            <button type="button" className="dw-button dw-button-danger" disabled={busy} onClick={() => { setAsking(false); start("demo", true); }}>
              <Icon name="repeat" size={18} />{t("demoReset")}</button>
            <button type="button" className="dw-button dw-button-quiet" disabled={busy} autoFocus onClick={() => setAsking(false)}>{t("cancel")}</button>
          </div>
        </div>
      ) : (
        <div className="dw-set-card">
          <span className="dw-set-card-icon"><Icon name="laptop" size={22} /></span>
          <span className="dw-set-row-main">
            <span className="dw-set-title">{t("demoCardTitle")}</span>
            <span className="dw-set-caption">{t("demoCardBody")}</span>
            <span className={`dw-set-state${demoMode ? " is-open" : ""}`}>{stateLine}</span>
          </span>
          <span className="dw-set-card-actions">
            {demoMode ? (
              <button type="button" className="dw-button" disabled={busy} onClick={() => start("own")}><Icon name="left" size={18} />{t("demoBack")}</button>
            ) : (
              <button type="button" className="dw-button dw-button-primary" disabled={busy} onClick={() => start("demo")}>{t("demoOpen")}</button>
            )}
            <button type="button" className="dw-button dw-button-quiet" disabled={busy} onClick={() => setAsking(true)}>{t("demoResetEllipsis")}</button>
          </span>
        </div>
      ))}
    </section>
  );
}
