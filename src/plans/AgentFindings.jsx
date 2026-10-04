import { useI18n } from "../i18n";
import { AreaGlyph } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { agentName, agentRole } from "../ui/agentName";
import { findingText, votesText } from "./findings";

/**
 * How the agents made a day's plans, one agent at a time and in the order they ran, each with its
 * one job in a line. An area agent lists what it found reviewing each of its tasks against all
 * your records, and the plans it voted for; the Orchestrator and the Summary agent say what they did.
 * @param {object} props
 * @param {object[]} props.route - The agents' runs that proposed the plans.
 */
export function AgentFindings({ route }) {
  const { t, language, demoText } = useI18n();
  return (
    <ol className="dw-agent-route">
      {route.map((run, index) => {
        const findings = (run.findings || []).map((finding) => [finding, findingText(finding, t, language, demoText)])
          .filter(([, text]) => text);
        return (
          <li key={`${run.agentKey}-${index}`}>
            <p className="dw-agent-route-name"><Icon name="agent" size={16} /><strong>{agentName(run.agentKey, t, run.phase)}</strong></p>
            {agentRole(run.agentKey, t) && <p className="dw-agent-role">{agentRole(run.agentKey, t)}</p>}
            {run.phase === "assessment" && Array.isArray(run.findings)
              ? findings.length > 0
                ? (
                  <ul className="dw-findings">
                    {findings.map(([finding, text], position) => (
                      <li key={`${finding.kind}-${finding.taskTitle || "area"}-${position}`}><AreaGlyph domain={finding.domain} /><span>{text}</span></li>
                    ))}
                  </ul>
                )
                : <p className="dw-caption">{t("agentNothingToReview", { area: t(run.agentKey) })}</p>
              : <p className="dw-caption">{demoText(run.summary)}</p>}
            {votesText(run.votes, t, demoText) && <p className="dw-caption">{votesText(run.votes, t, demoText)}</p>}
          </li>
        );
      })}
    </ol>
  );
}
