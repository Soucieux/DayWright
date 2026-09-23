import { useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Sheet } from "../ui/Sheet";

/**
 * A form in a sheet: its fields, one Save button and Cancel. It shows that it is saving, keeps the
 * sheet open with the reason when saving fails, and closes once the save succeeds.
 * @param {object} props
 * @param {string} props.title - The sheet's heading.
 * @param {string} props.submitLabel - The Save button's label.
 * @param {string} [props.note] - A line under the heading, such as who may read what is saved.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => Promise<void>} props.onSubmit - Save; throw to report a failure.
 * @param {() => void} props.onClose - Close the sheet.
 * @param {React.ReactNode} props.children - The form's fields.
 */
export function SheetForm({ title, submitLabel, note, backendConnected, onSubmit, onClose, children }) {
  const { t } = useI18n();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!backendConnected || saving) return;
    setSaving(true);
    setError("");
    try {
      await onSubmit();
      onClose();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet title={title} onClose={onClose}>
      <form className="dw-form" onSubmit={submit}>
        {note && <p className="dw-caption">{note}</p>}
        {children}
        {error && <p className="dw-alert" role="alert">{error}</p>}
        <div className="dw-actions">
          <button type="submit" className="dw-button dw-button-primary" disabled={!backendConnected || saving}>
            <Icon name="check" size={18} />{saving ? t("savingLabel") : submitLabel}
          </button>
          <button type="button" className="dw-button dw-button-quiet" onClick={onClose}>{t("cancel")}</button>
        </div>
        {!backendConnected && <p className="dw-caption">{t("previewCannotSave")}</p>}
      </form>
    </Sheet>
  );
}
