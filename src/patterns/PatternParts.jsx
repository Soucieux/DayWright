import { Fragment } from "react";
import { useI18n } from "../i18n";
import { AreaGlyph, areaOf } from "../ui/AreaTag";
import { GraphTips } from "../ui/GraphTips";
import { pairValue, stateNote } from "./patternText";

/**
 * A graph's finding: one sentence, its key figures bold, starting at the line's edge.
 * @param {object} props
 * @param {{text: string, strong: boolean}[]} props.parts - The sentence's parts, as patternText's leads give them.
 * @param {string} [props.className] - A class besides dw-pattern-lead.
 */
export function Lead({ parts, className = "" }) {
  return (
    <p className={`dw-pattern-lead ${className}`.trim()}>
      {parts.map((part, index) => (part.strong ? <strong key={index}>{part.text}</strong> : <Fragment key={index}>{part.text}</Fragment>))}
    </p>
  );
}

/**
 * How close a graph is to showing: a thin ink track and its count of its threshold.
 * @param {object} props
 * @param {{count: number, threshold: number, text: string}} props.progress - As stateNote gives it.
 */
function Threshold({ progress }) {
  return (
    <div className="dw-threshold">
      <span className="dw-threshold-track" aria-hidden="true"><span style={{ width: `${Math.min(progress.count / progress.threshold, 1) * 100}%` }} /></span>
      <span className="dw-caption">{progress.text}</span>
    </div>
  );
}

/**
 * One Patterns graph's card: its title, then until it has enough what it needs and how far along it is, or
 * the words for a range with nothing in it; once it shows, its finding, graph and key, and one caption line
 * saying what it counts, with a chip while it is still settling.
 * @param {object} props
 * @param {string} props.id - The heading's id.
 * @param {string} props.graph - The graph, as patternText names it.
 * @param {string} props.title - Its title.
 * @param {object} props.gauge - Its gauge, as the local service sends it.
 * @param {"week"|"month"|"all"} props.period - The range on show.
 * @param {string} props.caption - What it counts.
 * @param {string|null} [props.instead] - Words that stand in for the graph whatever its gauge, such as energy never reported.
 * @param {string} [props.className] - A class besides dw-card dw-pattern, such as an area's.
 * @param {import("react").ReactNode} props.children - Its finding, graph and key.
 */
export function PatternCard({ id, graph, title, gauge, period, caption, instead = null, className = "", children }) {
  const { t } = useI18n();
  const note = stateNote(graph, gauge, period, t);
  const shows = !instead && (note.state === "ready" || note.state === "settling");
  return (
    <section className={`dw-card dw-pattern ${className}`.trim()} aria-labelledby={id}>
      <div className="dw-card-head">
        <h2 id={id} className="dw-heading">{title}</h2>
        {shows && note.chip && <span className="dw-chip dw-chip-small dw-chip-settling">{note.chip}</span>}
      </div>
      {shows ? (
        <>
          {children}
          <p className="dw-caption dw-pattern-sub">{caption}</p>
        </>
      ) : (
        <>
          <p className="dw-muted">{instead || note.text}</p>
          {!instead && note.progress && <Threshold progress={note.progress} />}
        </>
      )}
    </section>
  );
}

/**
 * Planned against actual's rows: each its planned length hollow above the time it took filled, in its area's
 * colour, with both in figures and the change and count beside them; a row with too few fully done tasks
 * says how many it needs. A long name is cut, its tip saying it whole. A key names the two bars.
 * @param {object} props
 * @param {object[]} props.rows - As patterns.planned_actual gives them.
 * @param {string} props.label - The list's accessible name.
 * @param {boolean} [props.byTask=false] - Whether the rows are repeating tasks, named without an area glyph.
 */
export function PairList({ rows, label, byTask = false }) {
  const { t, language, demoText } = useI18n();
  const longest = Math.max(1, ...rows.filter((row) => row.planned != null).flatMap((row) => [row.planned, row.actual]));
  return (
    <>
      <GraphTips label={label}>
        <ul className={`dw-pair-list${byTask ? " is-tasks" : ""}`} aria-label={label}>
          {rows.map((row) => {
            const figures = pairValue(row, t, language);
            const name = row.title == null ? t(row.key) : demoText(row.title);
            return (
              <li key={row.key} data-mark aria-label={figures.needs ? `${name}: ${figures.needs}`
                : t("patternsPairRow", { name, value: figures.value, detail: figures.detail })}>
                <span className="dw-pair-name">{!byTask && <AreaGlyph domain={row.domain} />}<span>{name}</span></span>
                {figures.needs ? <span className="dw-caption dw-pair-needs">{figures.needs}</span> : (
                  <>
                    <span className={`dw-pair-bars dw-area-${areaOf(row.domain)}`} aria-hidden="true">
                      <span className="dw-pair-planned" style={{ width: `${(row.planned / longest) * 100}%` }} />
                      <span className="dw-pair-actual" style={{ width: `${(row.actual / longest) * 100}%` }} />
                    </span>
                    <span className="dw-pair-value" aria-hidden="true">{figures.value}<small>{figures.detail}</small></span>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      </GraphTips>
      <ul className="dw-scale-key">
        <li><span className="dw-pair-swatch is-planned" aria-hidden="true" />{t("patternsPlanned")}</li>
        <li><span className="dw-pair-swatch is-actual" aria-hidden="true" />{t("patternsActual")}</li>
      </ul>
    </>
  );
}
