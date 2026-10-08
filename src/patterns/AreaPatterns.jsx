import { useI18n } from "../i18n";
import { GraphTips } from "../ui/GraphTips";
import { Lead, PairList, PatternCard } from "./PatternParts";
import { energyLead, paceLead, paceRow, pairsLead } from "./patternText";

/**
 * An area page's repeating tasks, planned against actual, from every time recorded: what the one furthest
 * from plan usually takes, then a row per repeating task with any fully done time. An area with none has no card.
 * @param {object} props
 * @param {string} props.domain - The area.
 * @param {object} props.data - The area's overview, with its "patterns" from the local service.
 */
export function RepeatingCard({ domain, data }) {
  const { t, language } = useI18n();
  const repeating = data.patterns?.repeating;
  if (!repeating?.rows.length) return null;
  return (
    <PatternCard id={`dw-repeating-${domain}`} graph="repeating" title={t("patternPairs")} gauge={repeating} period="all"
      caption={t("patternPairsTasksCaption", { area: t(domain) })}>
      {repeating.finding && <Lead parts={pairsLead(repeating.finding, t, language, true)} />}
      <PairList rows={repeating.rows} label={t("patternsPairsTasksLabel")} byTask />
    </PatternCard>
  );
}

/**
 * Section pace's rows: each source's minutes a section in the Learn colour, with its sections; a long name is
 * cut, its tip saying it whole.
 * @param {object} props
 * @param {object[]} props.rows - As patterns.section_pace gives them.
 */
function PaceList({ rows }) {
  const { t, language, demoText } = useI18n();
  const longest = Math.max(1, ...rows.map((row) => row.minutes));
  return (
    <GraphTips label={t("patternsPaceLabel")}>
      <ul className="dw-pace-list" aria-label={t("patternsPaceLabel")}>
        {rows.map((row) => {
          const words = paceRow({ ...row, title: demoText(row.title) }, t, language);
          return (
            <li key={row.sourceId} data-mark aria-label={words.label}>
              <span className="dw-pace-name">{demoText(row.title)}</span>
              <span aria-hidden="true"><span className="dw-pace-bar" style={{ width: `${(row.minutes / longest) * 100}%` }} /></span>
              <span className="dw-pair-value" aria-hidden="true">{words.value}<small>{words.sections}</small></span>
            </li>
          );
        })}
      </ul>
    </GraphTips>
  );
}

/**
 * The Learn page's Section pace, from every learning task with a time: the fastest source, then each source's
 * minutes a section.
 * @param {object} props
 * @param {object} props.data - Learning's overview, with its "patterns" from the local service.
 */
export function PaceCard({ data }) {
  const { t, language } = useI18n();
  const pace = data.patterns?.pace;
  if (!pace) return null;
  return (
    <PatternCard id="dw-pace" graph="pace" title={t("patternPace")} gauge={pace} period="all" caption={t("patternPaceCaption")}
      className="dw-area-learn">
      {pace.finding && <Lead parts={paceLead(pace.finding, t, language)} />}
      <PaceList rows={pace.rows} />
    </PatternCard>
  );
}

/**
 * The one line Life's Energy card adds: how energy changes how long tasks take, from every time recorded; none
 * until enough days say, and none for energy never reported, which the card itself already shows.
 * @param {object} props
 * @param {object|null|undefined} props.finding - As patterns.energy gives it.
 */
export function EnergyLine({ finding }) {
  const { t } = useI18n();
  if (!["longer", "shorter", "hardly"].includes(finding?.kind)) return null;
  return <Lead parts={energyLead(finding, t, true)} className="dw-energy-line" />;
}
