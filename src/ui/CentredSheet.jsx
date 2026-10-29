import { createContext, useContext, useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "../i18n";
import { FOCUSABLE, nextFocus } from "./focusTrap";
import { Icon } from "./Icon";

/** How many centred panels are open; while any is, the app behind them is out of reach. */
let openCount = 0;
/** Who hears each change in that count (see subscribe). */
const listeners = new Set();
/**
 * Hear each change in how many centred panels are open.
 * @param {() => void} listener - Called after each change.
 * @returns {() => void} Stops hearing.
 */
function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Keep how many centred panels are open, and tell every listener.
 * @param {number} next - How many are open now.
 */
function setOpenCount(next) {
  openCount = next;
  for (const listener of listeners) listener();
}

/**
 * Whether a centred panel is open, for the app to make everything behind it inert.
 * @returns {boolean} True while one is.
 */
export function useCentredOpen() {
  return useSyncExternalStore(subscribe, () => openCount > 0);
}

/** The centred panel a control sits in, if any: `leave(then)` closes it first, asking when something in it changed. */
const CentredContext = createContext(null);

/**
 * The centred panel around a control, or null outside one.
 * @returns {{leave: (then: () => void) => void}|null} Leave it, then do something else.
 */
export function useCentred() {
  return useContext(CentredContext);
}

/**
 * A panel centred over the dimmed page, for a short job with one finish or for something app-wide: Settings, Open
 * with, Catch up, From a source, adding to the Library and a folder's sheets. It is about 560 px wide, or 720 px for
 * Settings and a folder's tree, at most 85% of the window's height with its content scrolling inside; on a phone it
 * fills the screen. Focus moves to its first field and stays inside it; everything behind is out of reach. Escape and
 * ✕ close it, and so does a click on the dimmed page, unless something in it changed and isn't saved. Focus returns to
 * whatever opened it.
 * @param {object} props
 * @param {string} props.title - Its heading.
 * @param {string} [props.name] - Its accessible name, when its heading names what it shows rather than the panel, as
 *   Settings' heading names the pane on show.
 * @param {React.ReactNode} [props.toolbar] - A toolbar under the heading, which then sits centred above it, as a Mac
 *   settings window has.
 * @param {string} [props.view] - Names the content on show; a new value moves focus to its first field.
 * @param {boolean} [props.wide=false] - Whether it is 720 px wide rather than 560.
 * @param {boolean} [props.changed] - Whether something in it changed and isn't saved, when its controls aren't fields
 *   whose input says so; by default any typing, ticking or choosing in it counts.
 * @param {() => void} props.onClose - Close it.
 * @param {React.ReactNode} props.children - Its content.
 */
export function CentredSheet({ title, name, toolbar, view, wide = false, changed, onClose, children }) {
  const { t } = useI18n();
  const titleId = useId();
  const panelRef = useRef(null);
  const openerRef = useRef(document.activeElement);
  const [edited, setEdited] = useState(false);
  // What to do once the user agrees to leave with their changes unsaved, while they are asked.
  const [leaving, setLeaving] = useState(null);
  const unsaved = changed ?? edited;

  useEffect(() => {
    setOpenCount(openCount + 1);
    const opener = openerRef.current;
    return () => {
      setOpenCount(openCount - 1);
      // Once the app behind is in reach again, as it isn't while this closes.
      window.setTimeout(() => (opener?.isConnected ? opener : document.querySelector("main"))?.focus());
    };
  }, []);

  useEffect(() => {
    const first = panelRef.current?.querySelector(".dw-centred-body")?.querySelector(FOCUSABLE);
    (first || panelRef.current?.querySelector("button"))?.focus();
  }, [view]);

  /** Escape closes the panel alone; Tab keeps focus inside it. */
  function onKeyDown(event) {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const controls = [...panelRef.current.querySelectorAll(FOCUSABLE)].filter((node) => node.offsetParent !== null);
    const next = nextFocus(controls.length, controls.indexOf(document.activeElement), event.shiftKey);
    event.preventDefault();
    if (next !== null) controls[next].focus();
  }

  /** A press on the dimmed page closes the panel, unless something in it changed; either way focus stays in it. */
  function onScrim(event) {
    if (event.target !== event.currentTarget) return;
    event.preventDefault();
    if (!unsaved) onClose();
  }

  /**
   * Close, then do what comes next once the app behind is in reach again, so a side panel it opens takes the focus.
   * @param {() => void} then - What to do next.
   */
  function closeThen(then) {
    onClose();
    window.setTimeout(then);
  }

  const context = {
    leave(then) {
      if (unsaved) setLeaving(() => then);
      else closeThen(then);
    },
  };

  return createPortal(
    <div className="dw-centred-scrim" onMouseDown={onScrim}>
      <section ref={panelRef} className={`dw-centred${wide ? " dw-centred-wide" : ""}`} role="dialog" aria-modal="true"
        aria-labelledby={name ? undefined : titleId} aria-label={name}
        onKeyDown={onKeyDown} onInput={() => setEdited(true)} onChange={() => setEdited(true)}>
        <header className={`dw-sheet-head${toolbar ? " dw-sheet-toolbar-head" : ""}`}>
          <h2 id={titleId} className="dw-heading">{title}</h2>
          <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("closeAction")} onClick={onClose}>
            <Icon name="x" size={20} /></button>
          {toolbar && <div className="dw-sheet-toolbar">{toolbar}</div>}
        </header>
        {leaving && (
          <div className="dw-centred-leave" role="alertdialog" aria-labelledby={`${titleId}-leave`}>
            <p id={`${titleId}-leave`}>{t("leaveUnsavedQuestion")}</p>
            <div className="dw-actions">
              <button type="button" className="dw-button dw-button-primary" onClick={() => closeThen(leaving)}>{t("leaveAction")}</button>
              <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setLeaving(null)}>{t("stayAction")}</button>
            </div>
          </div>
        )}
        <div className="dw-centred-body">
          <CentredContext.Provider value={context}>{children}</CentredContext.Provider>
        </div>
      </section>
    </div>,
    document.body,
  );
}
