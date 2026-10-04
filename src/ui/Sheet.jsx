import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "../i18n";
import { Icon } from "./Icon";

/**
 * A sheet beside the page on desktop, pushing it aside rather than covering it, and over the page on
 * phone, never over the bottom bar. Any screen may open one: it is drawn into the slot beside the
 * page. Focus moves to its first field on open and whenever its view changes, and returns on close
 * to whatever opened it, or to the page when that is gone. Escape closes it. A sheet that opens
 * another, as a goal opens one of its tasks, is hidden until that one closes, keeping what was typed.
 * @param {object} props
 * @param {string} props.title - The sheet's heading.
 * @param {string} [props.view] - Names the content on show; a new value moves focus to its first field.
 * @param {boolean} [props.hidden=false] - Whether it waits, out of sight, while another sheet is open.
 * @param {() => void} props.onClose - Close the sheet.
 * @param {React.ReactNode} props.children - The sheet's content.
 */
export function Sheet({ title, view, hidden = false, onClose, children }) {
  const { t } = useI18n();
  const titleId = useId();
  const sheetRef = useRef(null);
  const openerRef = useRef(document.activeElement);

  useEffect(() => {
    const sheet = sheetRef.current;
    const first = sheet?.querySelector(".dw-sheet-body input, .dw-sheet-body select, .dw-sheet-body textarea, .dw-sheet-body button");
    (first || sheet?.querySelector("button"))?.focus();
  }, [view]);

  useEffect(() => {
    const opener = openerRef.current;
    return () => (opener?.isConnected ? opener : document.querySelector("main"))?.focus();
  }, []);

  function onKeyDown(event) {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
    }
  }

  return createPortal(
    <aside className="dw-sheet" role="dialog" aria-labelledby={titleId} hidden={hidden} ref={sheetRef} onKeyDown={onKeyDown}>
      <header className="dw-sheet-head">
        <h2 id={titleId} className="dw-heading">{title}</h2>
        <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("closeAction")} onClick={onClose}><Icon name="x" size={20} /></button>
      </header>
      <div className="dw-sheet-body">{children}</div>
    </aside>,
    document.getElementById("dw-sheet-slot") || document.body,
  );
}
