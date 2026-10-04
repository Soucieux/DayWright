import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

/**
 * The one dropdown the interface uses: a button showing the chosen option that opens a menu of
 * options, each with an optional glyph and note, and a check on the chosen one. A disabled option
 * stays in the list with its note saying why. Arrow keys, Home and End move between the options
 * that can be chosen; Escape closes the menu and returns to the button.
 * @param {object} props
 * @param {string} props.label - What is being chosen, as the menu's accessible name.
 * @param {string} props.value - The chosen option's value.
 * @param {{value: string, label: string, icon?: string, note?: string, disabled?: boolean}[]} props.options - The options, in order.
 * @param {(value: string) => void} props.onChange - Choose another option.
 * @param {"field"|"compact"} [props.variant="field"] - As wide as a form field, or as wide as its text.
 * @param {string} [props.buttonLabel] - The button's accessible name; by default the label and the choice.
 * @param {string} [props.describedBy] - The id of text describing the choice, such as a clash.
 * @param {boolean} [props.disabled=false] - Unavailable, for example while nothing can be saved.
 * @param {string} [props.className] - A class for the dropdown's container, for its placement.
 */
export function MenuSelect({ label, value, options, onChange, variant = "field", buttonLabel, describedBy, disabled = false, className = "" }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const itemRefs = useRef([]);
  const current = options.find((option) => option.value === value);

  useEffect(() => {
    if (!open) return undefined;
    const chosen = options.findIndex((option) => option.value === value && !option.disabled);
    itemRefs.current[chosen >= 0 ? chosen : options.findIndex((option) => !option.disabled)]?.focus();
    function onPointer(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [open, value, options]);

  function close() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  /** Move focus to the next option that can be chosen, `step` places away, wrapping around. */
  function move(from, step) {
    for (let offset = 1; offset <= options.length; offset += 1) {
      const index = (from + step * offset + options.length * offset) % options.length;
      if (!options[index].disabled) {
        itemRefs.current[index]?.focus();
        return;
      }
    }
  }

  function onMenuKey(event) {
    const index = itemRefs.current.indexOf(document.activeElement);
    // Escape closes only the menu, not a sheet or panel the dropdown sits in.
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); }
    else if (event.key === "Tab") setOpen(false);
    else if (event.key === "ArrowDown") { event.preventDefault(); move(index, 1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); move(index, -1); }
    else if (event.key === "Home") { event.preventDefault(); move(-1, 1); }
    else if (event.key === "End") { event.preventDefault(); move(options.length, -1); }
  }

  function choose(option) {
    close();
    if (option.value !== value) onChange(option.value);
  }

  return (
    <div className={`dw-select-root ${className}`.trim()} ref={rootRef}>
      <button ref={triggerRef} type="button" className={`dw-select dw-select-${variant}`} aria-haspopup="menu" aria-expanded={open}
        aria-label={buttonLabel ?? `${label}: ${current?.label ?? value}`} aria-describedby={describedBy}
        disabled={disabled} onClick={() => setOpen((shown) => !shown)}>
        {current?.icon && <Icon name={current.icon} size={16} />}
        <span className="dw-select-value">{current?.label ?? value}</span>
        <Icon name="down" size={16} />
      </button>
      {open && (
        <div className={`dw-menu dw-menu-${variant}`} role="menu" aria-label={label} onKeyDown={onMenuKey}>
          {options.map((option, index) => (
            <button key={option.value} ref={(node) => { itemRefs.current[index] = node; }} type="button"
              role="menuitemradio" aria-checked={option.value === value} disabled={option.disabled} onClick={() => choose(option)}>
              {option.icon && <Icon name={option.icon} size={16} />}
              <span className="dw-menu-label">{option.label}{option.note && <small className="dw-menu-note">{option.note}</small>}</span>
              {option.value === value && <Icon name="check" size={16} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
