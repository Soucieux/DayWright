import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

/**
 * A button, primary unless plain, that opens a short menu of things to do, built like MenuSelect and using its menu:
 * the menu opens below the button, the first item takes focus, arrow keys, Home and End move between
 * the items, and Escape closes the menu and returns to the button. Choosing an item closes the menu.
 * @param {object} props
 * @param {string} props.label - The button's accessible name, which starts with its visible text.
 * @param {string} props.text - The button's visible text, after its plus.
 * @param {{value: string, label: string, icon?: string}[]} props.items - The menu's items, in order.
 * @param {(value: string) => void} props.onChoose - Do what an item names.
 * @param {boolean} [props.disabled=false] - Unavailable, for example while nothing can be saved.
 * @param {boolean} [props.plain=false] - A plain button rather than a primary one, where another action leads.
 */
export function ActionMenu({ label, text, items, onChoose, disabled = false, plain = false }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const itemRefs = useRef([]);

  useEffect(() => {
    if (!open) return undefined;
    itemRefs.current[0]?.focus();
    function onPointer(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [open]);

  function close() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  /** Move focus `step` items away from item `from`, wrapping around. */
  function move(from, step) {
    itemRefs.current[(from + step + items.length) % items.length]?.focus();
  }

  function onMenuKey(event) {
    const index = itemRefs.current.indexOf(document.activeElement);
    // Escape closes only the menu, not a sheet or panel the button sits in.
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); }
    else if (event.key === "Tab") setOpen(false);
    else if (event.key === "ArrowDown") { event.preventDefault(); move(index, 1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); move(index, -1); }
    else if (event.key === "Home") { event.preventDefault(); move(-1, 1); }
    else if (event.key === "End") { event.preventDefault(); move(items.length, -1); }
  }

  /** Close the menu, then do what the item names. */
  function choose(item) {
    setOpen(false);
    onChoose(item.value);
  }

  return (
    <div className="dw-select-root" ref={rootRef}>
      <button ref={triggerRef} type="button" className={plain ? "dw-button" : "dw-button dw-button-primary"} aria-haspopup="menu" aria-expanded={open}
        aria-label={label} disabled={disabled} onClick={() => setOpen((shown) => !shown)}>
        <Icon name="plus" size={18} />{text}<Icon name="down" size={16} />
      </button>
      {open && (
        <div className="dw-menu" role="menu" aria-label={label} onKeyDown={onMenuKey}>
          {items.map((item, index) => (
            <button key={item.value} ref={(node) => { itemRefs.current[index] = node; }} type="button" role="menuitem"
              onClick={() => choose(item)}>
              {item.icon && <Icon name={item.icon} size={16} />}
              <span className="dw-menu-label">{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
