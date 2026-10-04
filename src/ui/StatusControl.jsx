import { useI18n } from "../i18n";
import { Icon } from "./Icon";
import { MenuSelect } from "./MenuSelect";

/** The four reported states, in menu order. Each glyph's shape carries the meaning without colour. */
export const STATUSES = ["planned", "done", "partial", "skipped"];

/**
 * Report what actually happened to one task or plan entry. Only the user changes a status; nothing
 * here infers one from the time of day.
 * @param {object} props
 * @param {string} props.value - The current status.
 * @param {(status: string) => void} [props.onChange] - Report a new status.
 * @param {string} props.title - The task title, spoken in the control's accessible name.
 * @param {"compact"|"segmented"} [props.variant="compact"] - A menu button, or four visible options.
 * @param {boolean} [props.readOnly=false] - Show the status as text, for history.
 * @param {boolean} [props.disabled=false] - Unavailable, for example while nothing can be saved.
 * @param {boolean} [props.paused=false] - The task's goal is paused, so it shows Paused and can't be
 *   reported; a task is never paused on its own.
 */
export function StatusControl({ value, onChange, title, variant = "compact", readOnly = false, disabled = false, paused = false }) {
  const { t } = useI18n();
  // Paused comes first: a paused task shows Paused even where its status is only read.
  if (paused) {
    return <span className="dw-status-paused" title={t("taskGoalPaused")}><Icon name="pause" size={16} />{t("paused")}</span>;
  }
  if (readOnly) {
    return <span className="dw-status-readonly"><Icon name={`status-${value}`} size={16} />{t(value)}</span>;
  }
  if (variant === "segmented") {
    return (
      <div className="dw-status-segmented" role="radiogroup" aria-label={`${t("statusFor")} ${title}`}>
        {STATUSES.map((status) => (
          <button key={status} type="button" role="radio" aria-checked={value === status} disabled={disabled}
            onClick={() => value !== status && onChange(status)}>
            <Icon name={`status-${status}`} size={16} />{t(status)}
          </button>
        ))}
      </div>
    );
  }
  return (
    <MenuSelect variant="compact" className="dw-status-menu" label={`${t("statusFor")} ${title}`} value={value}
      buttonLabel={`${t("statusFor")} ${title}: ${t(value)}. ${t("changeStatus")}`} disabled={disabled} onChange={onChange}
      options={STATUSES.map((status) => ({ value: status, label: t(status), icon: `status-${status}` }))} />
  );
}
