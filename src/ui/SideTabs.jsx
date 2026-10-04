import { useRef, useState } from "react";

/**
 * Views that share a page's side column, one at a time, chosen by tabs that the arrow keys also
 * move between. The first tab shows first.
 * @param {object} props
 * @param {string} props.label - Names the tab list for assistive technology.
 * @param {Array<[string, string, import("react").ReactNode]>} props.tabs - Each tab's id, label and content.
 */
export function SideTabs({ label, tabs }) {
  const [selected, setSelected] = useState(tabs[0][0]);
  const tabRefs = useRef({});
  const [currentId, , content] = tabs.find(([id]) => id === selected) || tabs[0];

  /**
   * Move to the next or previous tab with the arrow keys, as a tab list does.
   * @param {KeyboardEvent} event - The key pressed on a tab.
   */
  function onKeyDown(event) {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const index = tabs.findIndex(([id]) => id === currentId);
    const [next] = tabs[(index + step + tabs.length) % tabs.length];
    setSelected(next);
    tabRefs.current[next]?.focus();
  }

  return (
    <>
      <div className="dw-tabs" role="tablist" aria-label={label} onKeyDown={onKeyDown}>
        {tabs.map(([id, text]) => (
          <button key={id} ref={(node) => { tabRefs.current[id] = node; }} type="button" role="tab" id={`dw-side-tab-${id}`}
            aria-selected={currentId === id} aria-controls="dw-side-panel" tabIndex={currentId === id ? 0 : -1}
            onClick={() => setSelected(id)}>{text}</button>
        ))}
      </div>
      <div id="dw-side-panel" role="tabpanel" aria-labelledby={`dw-side-tab-${currentId}`} className="dw-column-side">
        {content}
      </div>
    </>
  );
}
