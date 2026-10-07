import { useI18n } from "../i18n";
import { StatusControl } from "../ui/StatusControl";
import { Segmented } from "../ui/Segmented";
import { CHOICE_KEYS, choiceOptions } from "./catchUp";

/**
 * A day's tasks to catch up on, in time order with untimed ones last, as Today's sheet and Ava's card
 * show them: each with its time, its status now, and its choice of As is, Done, Partly done or Skip.
 * @param {object} props
 * @param {{id: string, title: string, start: string|null, status: string, noReply: boolean}[]} props.tasks - As the
 *   service lists them.
 * @param {Object<string, string>} props.choices - Each task's choice, by id.
 * @param {(id: string, choice: string) => void} props.onChoose - Change a task's choice.
 */
export function CatchUpList({ tasks, choices, onChoose }) {
  const { t, demoText } = useI18n();
  return (
    <ol className="dw-catch-up">
      {tasks.map((task) => (
        <li key={task.id} className="dw-catch-up-row">
          <div className="dw-catch-up-task">
            <span className="dw-catch-up-title">{demoText(task.title)}</span>
            <span className="dw-catch-up-meta">
              <span className="dw-catch-up-time">{task.start || t("untimed")}</span>
              <StatusControl value={task.status} title={demoText(task.title)} readOnly noReply={task.noReply} />
            </span>
          </div>
          <Segmented label={t("catchUpChoiceFor", { title: demoText(task.title) })} value={choices[task.id]}
            onChange={(choice) => onChoose(task.id, choice)} className="dw-catch-up-choices"
            options={choiceOptions(task).map((choice) => [choice, t(CHOICE_KEYS[choice])])} />
        </li>
      ))}
    </ol>
  );
}
