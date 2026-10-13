import { useContext } from "react";
import { useI18n } from "../i18n";
import { WorkspaceSwitchContext } from "../settings/useWorkspaceSwitch";
import { Icon } from "./Icon";

/**
 * The banner on every screen while the demo is open: it says so, that the user's own data is untouched, and goes
 * back to it through the window's one switch (see useWorkspaceSwitch), whose overlay then says what is happening.
 */
export function DemoBanner() {
  const { t, language } = useI18n();
  const { switching, start } = useContext(WorkspaceSwitchContext);
  return (
    <div className="dw-banner dw-banner-demo dw-demo-stripe dw-demo-banner" lang={language === "zh" ? "zh-Hans" : "en"}>
      <Icon name="laptop" size={18} />
      <p className="dw-demo-banner-text"><strong>{t("demoBannerTitle")}</strong><span aria-hidden="true"> · </span>{t("demoBannerUntouched")}</p>
      <button type="button" className="dw-button dw-button-quiet dw-demo-back" disabled={Boolean(switching)} onClick={() => start("own")}>
        <Icon name="left" size={16} />{t("demoBack")}</button>
    </div>
  );
}
