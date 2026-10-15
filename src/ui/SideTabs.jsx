import { useState } from "react";
import { TabList } from "./TabList";

/**
 * Views that share a page's side column, one at a time, chosen by tabs that the arrow keys also
 * move between. The first tab shows first.
 * @param {object} props
 * @param {string} props.label - Names the tab list for assistive technology.
 * @param {Array<[string, string, import("react").ReactNode]>} props.tabs - Each tab's id, label and content.
 */
export function SideTabs({ label, tabs }) {
  const [selected, setSelected] = useState(tabs[0][0]);
  const [currentId, , content] = tabs.find(([id]) => id === selected) || tabs[0];

  return (
    <>
      <TabList label={label} idBase="dw-side" tabs={tabs} selected={currentId} onSelect={setSelected} />
      <div id="dw-side-panel" role="tabpanel" aria-labelledby={`dw-side-tab-${currentId}`} className="dw-column-side">
        {content}
      </div>
    </>
  );
}
