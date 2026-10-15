import { useRef } from "react";
import { tabAfter } from "./tabs";

/**
 * A page's tabs, one chosen at a time, which the arrow keys also move between; the chosen one alone is in the tab
 * order. Each tab controls the one panel the page draws under it, `${idBase}-panel`, labelled by the chosen tab.
 * @param {object} props
 * @param {string} props.label - Names the tab list for assistive technology.
 * @param {string} props.idBase - The start of the tabs' and the panel's ids.
 * @param {Array<[string, import("react").ReactNode]>} props.tabs - Each tab's id and label, in order.
 * @param {string} props.selected - The chosen tab's id.
 * @param {(id: string) => void} props.onSelect - Choose a tab.
 * @param {Record<string, string>} [props.names] - A tab's name for screen readers, by its id, where its label won't
 *   read well aloud, as "Folders, 3" for "Folders · 3".
 */
export function TabList({ label, idBase, tabs, selected, onSelect, names }) {
  const tabRefs = useRef({});

  /**
   * Move to the next or previous tab with the arrow keys.
   * @param {KeyboardEvent} event - The key pressed on a tab.
   */
  function onKeyDown(event) {
    const next = tabAfter(tabs.map(([id]) => id), selected, event.key);
    if (!next) return;
    event.preventDefault();
    onSelect(next);
    tabRefs.current[next]?.focus();
  }

  return (
    <div className="dw-tabs" role="tablist" aria-label={label} onKeyDown={onKeyDown}>
      {tabs.map(([id, text]) => (
        <button key={id} ref={(node) => { tabRefs.current[id] = node; }} type="button" role="tab" id={`${idBase}-tab-${id}`}
          aria-selected={selected === id} aria-controls={`${idBase}-panel`} tabIndex={selected === id ? 0 : -1}
          aria-label={names?.[id]} onClick={() => onSelect(id)}>{text}</button>
      ))}
    </div>
  );
}
