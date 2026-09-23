import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "./Icon";

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
 */
export function StatusControl({ value, onChange, title, variant = "compact", readOnly = false, disabled = false }) {
  const { t } = useI18n();
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
  return <StatusMenu value={value} onChange={onChange} title={title} disabled={disabled} />;
}

/** The compact form: a button naming the status that opens a four-item menu. */
function StatusMenu({ value, onChange, title, disabled }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const itemRefs = useRef([]);

  useEffect(() => {
    if (!open) return undefined;
    itemRefs.current[STATUSES.indexOf(value)]?.focus();
    function onPointer(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [open, value]);

  function close() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  function onMenuKey(event) {
    const index = itemRefs.current.indexOf(document.activeElement);
    if (event.key === "Escape") { event.preventDefault(); close(); }
    else if (event.key === "ArrowDown") { event.preventDefault(); itemRefs.current[(index + 1) % STATUSES.length]?.focus(); }
    else if (event.key === "ArrowUp") { event.preventDefault(); itemRefs.current[(index + STATUSES.length - 1) % STATUSES.length]?.focus(); }
  }

  function choose(status) {
    close();
    if (status !== value) onChange(status);
  }

  return (
    <div className="dw-status-menu" ref={rootRef}>
      <button ref={triggerRef} type="button" className="dw-status-button" aria-haspopup="menu" aria-expanded={open}
        aria-label={`${t("statusFor")} ${title}: ${t(value)}. ${t("changeStatus")}`} disabled={disabled}
        onClick={() => setOpen((current) => !current)}>
        <Icon name={`status-${value}`} size={16} />{t(value)}<Icon name="down" size={16} />
      </button>
      {open && (
        <div className="dw-menu" role="menu" aria-label={`${t("statusFor")} ${title}`} onKeyDown={onMenuKey}>
          {STATUSES.map((status, index) => (
            <button key={status} ref={(node) => { itemRefs.current[index] = node; }} type="button"
              role="menuitemradio" aria-checked={value === status} onClick={() => choose(status)}>
              <Icon name={`status-${status}`} size={16} /><span>{t(status)}</span>
              {value === status && <Icon name="check" size={16} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
