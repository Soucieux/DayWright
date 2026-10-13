import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";

/**
 * The whole window while it switches workspace (see useWorkspaceSwitch): what is happening, a bar that moves while it
 * waits, and that the window loads again when it is ready. Nothing behind it can be reached: the app is inert, a
 * click lands here, and Escape is held so no sheet closes under it. A switch that failed says why, with Close.
 * @param {object} props
 * @param {string|null} props.switching - The message key while under way.
 * @param {{key?: string, text?: string, reload: boolean}|null} props.failed - Why it failed.
 * @param {() => void} props.close - Close a failed switch's message.
 */
export function SwitchOverlay({ switching, failed, close }) {
  const { t } = useI18n();
  const ref = useRef(null);

  useEffect(() => {
    ref.current?.focus();
    const hold = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };
    window.addEventListener("keydown", hold, true);
    return () => window.removeEventListener("keydown", hold, true);
  }, []);

  return (
    <div className="dw-switch-overlay" role="dialog" aria-modal="true" aria-labelledby="dw-switch-title" tabIndex={-1} ref={ref}>
      <div className="dw-switch-card">
        <span className="dw-switch-icon"><Icon name={failed ? "alert" : "laptop"} size={22} /></span>
        <p id="dw-switch-title" className="dw-heading" aria-live="polite">
          {failed ? (failed.key ? t(failed.key) : failed.text) : t(switching)}</p>
        {failed ? (
          <button type="button" className="dw-button" autoFocus onClick={close}>{t(failed.reload ? "demoContinue" : "closeAction")}</button>
        ) : (
          <>
            <div className="dw-switch-bar" role="progressbar" aria-labelledby="dw-switch-title"><span /></div>
            <p className="dw-caption">{t("demoSwitchNote")}</p>
          </>
        )}
      </div>
    </div>
  );
}
