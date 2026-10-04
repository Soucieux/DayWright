import { useI18n } from "../i18n";
import { timeColumn } from "../records/taskDraft";

/**
 * A schedule row's time column, the same for a task, a plan's entry or a meal: its start, with its
 * length directly below it; a task with no start shows its length alone.
 * @param {object} props
 * @param {{start_time: string|null, duration_minutes: number}} props.row - The row.
 */
export function TimeColumn({ row }) {
  const { language } = useI18n();
  const { start, length } = timeColumn(row, language);
  return (
    <div className="dw-row-time">
      {start && <span className="dw-row-start">{start}</span>}
      <span className={start ? "dw-caption" : "dw-row-start"}>{length}</span>
    </div>
  );
}
