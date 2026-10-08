import { useLayoutEffect, useRef, useState } from "react";
import { markText, moveMark } from "./tipMarks";

/**
 * A graph whose marks each show a small ink tip with the same words as their accessible name, on hover, on
 * a tap and on keyboard focus. The graph is one tab stop: the arrow keys move between its marks, the tip
 * following, and Escape hides it. A tip adds to the words the graph already has, never replaces them, and
 * a screen reader hears each mark as the keys reach it.
 * @param {object} props
 * @param {string} props.label - The graph's accessible name.
 * @param {number} [props.columns=0] - The marks in a row of a grid, for the up and down keys; 0 for one row.
 * @param {string} [props.className] - A class besides dw-tip-wrap.
 * @param {import("react").ReactNode} props.children - The graph, whose marks carry data-mark.
 */
export function GraphTips({ label, columns = 0, className = "", children }) {
  const wrap = useRef(null);
  const tipRef = useRef(null);
  const [shown, setShown] = useState({ index: -1, text: "", left: 0, top: 0, visible: false });
  const [focused, setFocused] = useState(false);
  const marks = () => [...(wrap.current?.querySelectorAll("[data-mark]") || [])];

  /**
   * Show a mark's tip over it, and mark it as the one shown.
   * @param {number} index - The mark, in the graph's order.
   */
  function show(index) {
    const all = marks();
    const mark = all[index];
    if (!mark || !wrap.current) return;
    all.forEach((each, at) => each.classList.toggle("is-active", at === index));
    const box = wrap.current.getBoundingClientRect();
    const place = mark.getBoundingClientRect();
    setShown({ index, text: markText(mark), left: place.left - box.left + place.width / 2, top: place.top - box.top, visible: true });
  }

  function hide() {
    marks().forEach((each) => each.classList.remove("is-active"));
    setShown((now) => ({ ...now, visible: false }));
  }

  // A tip near the graph's edge stays within it.
  useLayoutEffect(() => {
    const tip = tipRef.current;
    if (!shown.visible || !tip || !wrap.current) return;
    const half = tip.offsetWidth / 2;
    const left = Math.min(Math.max(shown.left, half), Math.max(wrap.current.clientWidth - half, half));
    if (left !== shown.left) setShown((now) => ({ ...now, left }));
  }, [shown]);

  /** Show the tip of the mark under the pointer or a tap. */
  function onPointer(event) {
    const mark = event.target.closest?.("[data-mark]");
    if (mark && wrap.current?.contains(mark)) show(marks().indexOf(mark));
  }

  function onKeyDown(event) {
    const next = moveMark(event.key, shown.visible ? shown.index : -1, marks().length, columns);
    if (next === null) return;
    event.preventDefault();
    if (next < 0) hide();
    else show(next);
  }

  return (
    <div ref={wrap} className={`dw-tip-wrap ${className}`.trim()} tabIndex={0} role="group" aria-label={label}
      onMouseOver={onPointer} onClick={onPointer} onMouseLeave={() => { if (!focused) hide(); }}
      onFocus={(event) => { if (event.target === wrap.current) { setFocused(true); show(Math.max(shown.index, 0)); } }}
      onBlur={() => { setFocused(false); hide(); }} onKeyDown={onKeyDown}>
      {children}
      {shown.visible && <span ref={tipRef} className="dw-tip" aria-hidden="true" style={{ left: shown.left, top: shown.top }}>{shown.text}</span>}
      <span className="dw-visually-hidden" aria-live="polite">{focused && shown.visible ? shown.text : ""}</span>
    </div>
  );
}
