import { useI18n } from "../i18n";
import { Icon } from "./Icon";

/**
 * The banners every page carries while its state needs saying out loud: nothing is being saved,
 * the data is the demo workspace's, or the plan is an old example rather than the user's own.
 * @param {object} props
 * @param {object} props.day - The day on show.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 */
export function PageBanners({ day, backendConnected }) {
  const { t } = useI18n();
  return (
    <>
      {!backendConnected && <p className="dw-banner dw-banner-caution" role="status"><Icon name="alert" size={18} />{t("previewBanner")}</p>}
      {day.demoMode && <p className="dw-banner dw-banner-demo dw-demo-stripe" role="note"><Icon name="laptop" size={18} /><span><strong>{t("saveDemo")}</strong> · {t("demoCopy")}</span></p>}
      {day.planSource === "deterministic-v1" && <p className="dw-banner dw-banner-caution" role="note"><Icon name="alert" size={18} /><span><strong>{t("examplePlan")}</strong> · {t("examplePlanHelp")}</span></p>}
    </>
  );
}
