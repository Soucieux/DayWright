import { useI18n } from "../i18n";
import { DemoBanner } from "./DemoBanner";
import { Icon } from "./Icon";

/**
 * The banners every page carries while its state needs saying out loud: nothing is being saved, or
 * the demo is open (see DemoBanner).
 * @param {object} props
 * @param {object} props.day - The day on show.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 */
export function PageBanners({ day, backendConnected }) {
  const { t } = useI18n();
  return (
    <>
      {!backendConnected && <p className="dw-banner dw-banner-caution" role="status"><Icon name="alert" size={18} />{t("previewBanner")}</p>}
      {day.demoMode && <DemoBanner />}
    </>
  );
}
