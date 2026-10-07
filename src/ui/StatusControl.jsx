import { useI18n } from "../i18n";
import { Icon } from "./Icon";
import { MenuSelect } from "./MenuSelect";

/** The four reported states, in menu order. Each glyph's shape carries the meaning without colour. */
export const STATUSES = ["planned", "done", "partial", "skipped"];

/** What a task left without a status once its day's 22:00 passed reads, as DayWright marks it, and its glyph. */
const NO_REPLY = "noReply";
const NO_REPLY_GLYPH = "status-noreply";

/**
 * Report what actually happened to one task or plan entry. Only the user sets Done, Partial or
 * Skipped; a task still without one once its day's 22:00 passed reads "Not done · no reply", which
 * DayWright marks, and any status may still be set over it.
 * @param {object} props
 * @param {string} props.value - The current status.
 * @param {(status: string) => void} [props.onChange] - Report a new status.
 * @param {string} props.title - The task title, spoken in the control's accessible name.
 * @param {"compact"|"segmented"} [props.variant="compact"] - A menu button, or four visible options.
 * @param {boolean} [props.readOnly=false] - Show the status as text, for history.
 * @param {boolean} [props.disabled=false] - Unavailable, for example while nothing can be saved.
 * @param {boolean} [props.paused=false] - The task's goal is paused, so it shows Paused and can't be
 *   reported; a task is never paused on its own.
 * @param {boolean} [props.noReply=false] - The task reads "Not done · no reply".
 */
export function StatusControl({ value, onChange, title, variant = "compact", readOnly = false, disabled = false, paused = false,
  noReply = false }) {
  const { t } = useI18n();
  const shown = noReply ? NO_REPLY : value;
  const glyph = noReply ? NO_REPLY_GLYPH : `status-${value}`;
  // Paused comes first: a paused task shows Paused even where its status is only read.
  if (paused) {
    return <span className="dw-status-paused" title={t("taskGoalPaused")}><Icon name="pause" size={16} />{t("paused")}</span>;
  }
  if (readOnly) {
    return <span className="dw-status-readonly"><Icon name={glyph} size={16} />{t(shown)}</span>;
  }
  if (variant === "segmented") {
    return (
      <>
        {noReply && <p className="dw-status-readonly"><Icon name={NO_REPLY_GLYPH} size={16} />{t(NO_REPLY)}</p>}
        <div className="dw-status-segmented" role="radiogroup" aria-label={`${t("statusFor")} ${title}`}>
          {STATUSES.map((status) => (
            <button key={status} type="button" role="radio" aria-checked={shown === status} disabled={disabled}
              onClick={() => shown !== status && onChange(status)}>
              <Icon name={`status-${status}`} size={16} />{t(status)}
            </button>
          ))}
        </div>
      </>
    );
  }
  // No reply shows as the choice made, and isn't one to pick.
  const options = STATUSES.map((status) => ({ value: status, label: t(status), icon: `status-${status}` }));
  return (
    <MenuSelect variant="compact" className="dw-status-menu" label={`${t("statusFor")} ${title}`} value={shown}
      buttonLabel={`${t("statusFor")} ${title}: ${t(shown)}. ${t("changeStatus")}`} disabled={disabled} onChange={onChange}
      options={noReply ? [{ value: NO_REPLY, label: t(NO_REPLY), icon: NO_REPLY_GLYPH, disabled: true }, ...options] : options} />
  );
}
