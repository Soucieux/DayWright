import { useI18n } from "../i18n";
import { timeColumn } from "../records/taskDraft";

/**
 * A schedule row's time column, the same for a task, a plan's entry or a meal: its start, with its
 * length directly below it; a task with no start shows its length alone. Once a task's status set
 * the time it took, the column shows when it started and that time.
 * @param {object} props
 * @param {{start_time: string|null, duration_minutes: number}} props.row - The row.
 */
export function TimeColumn({ row }) {
  const { t, language } = useI18n();
  const { start, length, taken } = timeColumn(row, language);
  return (
    <div className="dw-row-time">
      {start && <span className="dw-row-start">{start}</span>}
      <span className={start ? "dw-caption" : "dw-row-start"}>
        {/* A no-break space keeps the hidden word apart from the time, which a plain space beside it loses. */}
        {taken && <span className="dw-visually-hidden">{`${t("tookPrefix")} `}</span>}{length}
      </span>
    </div>
  );
}
