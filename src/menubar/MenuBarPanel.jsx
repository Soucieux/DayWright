import { useEffect, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaTag } from "../ui/AreaTag";
import { StatusControl } from "../ui/StatusControl";
import { askShell, taskFacts } from "./panel";

/** One minute, in milliseconds. */
const MINUTE_MS = 60 * 1000;

/**
 * The menu bar's panel: the task current now and the next one, each with its own status control, and
 * a way into DayWright. It renews at each minute's turn and whenever it is shown, and after a report it
 * asks the shell to renew the menu bar's title. Nothing here notifies.
 */
export function MenuBarPanel() {
  const { t } = useI18n();
  const [now, setNow] = useState(null);
  const [failed, setFailed] = useState(false);

  async function load() {
    try {
      setNow(await api("/api/now"));
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }

  useEffect(() => {
    load();
    let timer;
    const tick = () => {
      load();
      timer = setTimeout(tick, MINUTE_MS - (Date.now() % MINUTE_MS));
    };
    timer = setTimeout(tick, MINUTE_MS - (Date.now() % MINUTE_MS));
    window.addEventListener("focus", load);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("focus", load);
    };
  }, []);

  /**
   * Report a task, then show the panel and the menu bar's title as they now stand.
   * @param {object} task - The current or next task.
   * @param {string} status - The status chosen.
   */
  async function report(task, status) {
    try {
      await api(`/api/daily-items/${task.id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    } catch {
      setFailed(true);
    }
    await load();
    askShell("refresh");
  }

  return (
    <main className="dw-menubar">
      <PanelTask label={t("menubarNow")} task={now?.current} taken={now?.taken ?? 0} empty={t("menubarNothingNow")} onStatus={report} />
      <PanelTask label={t("menubarNext")} task={now?.next} taken={null} empty={t("menubarNothingNext")} onStatus={report} />
      {failed && <p className="dw-menubar-note" role="status">{t("menubarUnavailable")}</p>}
      <button type="button" className="dw-button dw-button-primary dw-menubar-open" onClick={() => askShell("open")}>
        {t("openDayWright")}
      </button>
    </main>
  );
}

/**
 * One of the panel's two tasks: its full title and area, what it has taken or when it starts, its set
 * time, and its status control; or a line saying there is none.
 * @param {object} props
 * @param {string} props.label - "Now" or "Next".
 * @param {object|null|undefined} props.task - The task from /api/now.
 * @param {number|null} props.taken - The minutes the current task has taken, or null for the next one.
 * @param {string} props.empty - What to say when there is no such task.
 * @param {(task: object, status: string) => void} props.onStatus - Report the task.
 */
function PanelTask({ label, task, taken, empty, onStatus }) {
  const { t, language, demoText } = useI18n();
  return (
    <section className="dw-menubar-task" aria-label={label}>
      <p className="dw-eyebrow">{label}</p>
      {task ? (
        <>
          <h2 className="dw-menubar-title">{demoText(task.title)}</h2>
          <p className="dw-menubar-facts"><AreaTag domain={task.domain} />{taskFacts(task, taken, t, language).join(" · ")}</p>
          <StatusControl variant="segmented" value={task.status} title={demoText(task.title)} onChange={(status) => onStatus(task, status)} />
        </>
      ) : <p className="dw-menubar-empty">{empty}</p>}
    </section>
  );
}
