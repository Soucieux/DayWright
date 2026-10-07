import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Sheet } from "../ui/Sheet";
import { CatchUpList } from "./CatchUpList";
import { chosenStatuses, firstChoices } from "./catchUp";

/**
 * Catch up on today's tasks at once, from Today or Tasks: every task today in time order, untimed ones
 * last, each left as it is or given Done, Partly done or Skip; a task with a status shows it, to change.
 * One Save applies them all, and its notice offers Undo for a few seconds.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(statuses: Object<string, string>) => Promise<boolean>} props.onSave - Save the statuses chosen,
 *   by task id; true once saved.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function CatchUpSheet({ backendConnected, onSave, onClose }) {
  const { t } = useI18n();
  const [tasks, setTasks] = useState(null);
  const [choices, setChoices] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let current = true;
    api("/api/catch-up")
      .then((listed) => {
        if (!current) return;
        setTasks(listed.tasks);
        setChoices(firstChoices(listed.tasks));
      })
      .catch((caught) => {
        if (!current) return;
        setTasks([]);
        setError(caught.message);
      });
    return () => { current = false; };
  }, []);

  const statuses = tasks ? chosenStatuses(tasks, choices) : {};
  const count = Object.keys(statuses).length;

  async function save() {
    setSaving(true);
    if (await onSave(statuses)) onClose();
    else setSaving(false);
  }

  return (
    <Sheet title={t("catchUpTitle")} view={tasks ? "tasks" : "loading"} onClose={onClose}>
      <p className="dw-caption">{t("catchUpLead")}</p>
      {tasks === null ? <p className="dw-caption" role="status">{t("catchUpLoading")}</p>
        : error ? <p className="dw-alert" role="alert">{error}</p>
          : tasks.length === 0 ? <p className="dw-caption">{t("catchUpEmpty")}</p>
            : <CatchUpList tasks={tasks} choices={choices} onChoose={(id, choice) => setChoices((now) => ({ ...now, [id]: choice }))} />}
      {tasks?.length > 0 && (
        <div className="dw-actions dw-catch-up-save">
          <p className="dw-caption" aria-live="polite">
            {count === 0 ? t("catchUpNoChanges") : count === 1 ? t("catchUpChangesOne") : t("catchUpChanges", { count })}
          </p>
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected || count === 0 || saving}
            aria-busy={saving} onClick={save}><Icon name="check" size={18} />{t("catchUpSave")}</button>
        </div>
      )}
    </Sheet>
  );
}
