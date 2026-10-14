import { useContext, useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { WorkspaceSwitchContext } from "./useWorkspaceSwitch";

/**
 * Settings › Demo: two months of made-up use in a workspace of its own, opened here and left here or from its
 * banner, through the window's one switch (see useWorkspaceSwitch), whose overlay says what is happening; every button
 * here is off while it does. Reset asks first, then deletes the demo and makes it anew, ending today; whatever was
 * done in it until then is gone, and the user's own data is never touched.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the demo is open.
 */
export function DemoSection({ backendConnected, demoMode }) {
  const { t } = useI18n();
  const { switching, start } = useContext(WorkspaceSwitchContext);
  const [asking, setAsking] = useState(false);
  const busy = Boolean(switching);

  return (
    <section className="dw-settings-section" aria-labelledby="dw-settings-demo">
      <h3 id="dw-settings-demo" className="dw-section-label">{t("settingsDemo")}</h3>
      <p className="dw-muted">{t("demoLead")}</p>
      {!backendConnected ? <p className="dw-muted">{t("settingsServiceOff")}</p> : asking ? (
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
        <>
          <p className="dw-caption">{t(demoMode ? "demoOpenNote" : "demoKeptNote")}</p>
          <div className="dw-actions">
            {demoMode ? (
              <button type="button" className="dw-button" disabled={busy} onClick={() => start("own")}><Icon name="left" size={18} />{t("demoBack")}</button>
            ) : (
              <button type="button" className="dw-button" disabled={busy} onClick={() => start("demo")}><Icon name="laptop" size={18} />{t("demoOpen")}</button>
            )}
            <button type="button" className="dw-button dw-button-quiet" disabled={busy} onClick={() => setAsking(true)}>
              <Icon name="repeat" size={18} />{t("demoResetEllipsis")}</button>
          </div>
        </>
      )}
    </section>
  );
}
