import { useEffect, useRef } from "react";
import { useI18n } from "../i18n";
import { Icon } from "./Icon";

/**
 * A sheet beside the page on desktop, pushing it aside rather than covering it, and over the page on
 * phone, never over the bottom bar. Focus moves to its first field on open and whenever its view
 * changes, and returns on close to whatever opened it, or to the page when that is gone. Escape
 * closes it.
 * @param {object} props
 * @param {string} props.title - The sheet's heading.
 * @param {string} [props.view] - Names the content on show; a new value moves focus to its first field.
 * @param {() => void} props.onClose - Close the sheet.
 * @param {React.ReactNode} props.children - The sheet's content.
 */
export function Sheet({ title, view, onClose, children }) {
  const { t } = useI18n();
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

  return (
    <aside className="dw-sheet" role="dialog" aria-labelledby="dw-sheet-title" ref={sheetRef} onKeyDown={onKeyDown}>
      <header className="dw-sheet-head">
        <h2 id="dw-sheet-title" className="dw-heading">{title}</h2>
        <button type="button" className="dw-icon-button" aria-label={t("closeAction")} onClick={onClose}><Icon name="x" size={20} /></button>
      </header>
      <div className="dw-sheet-body">{children}</div>
    </aside>
  );
}
