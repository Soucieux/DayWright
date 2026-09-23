import { Fragment, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { agentName } from "../ui/agentName";

/**
 * The agents that worked on a reply, in order, and what each one did.
 * @param {object} props
 * @param {object[]} props.route - The agent runs, each with `agentKey` and `summary`.
 * @param {() => void} props.onHide - Fold the route away.
 */
function AgentRoute({ route, onHide }) {
  const { t, demoText } = useI18n();
  return (
    <section className="dw-route" aria-label={t("routeHeading")}>
      <div className="dw-card-head">
        <h4 className="dw-section-label">{t("routeHeading")}</h4>
        <button type="button" className="dw-link" onClick={onHide}>{t("hideAction")}</button>
      </div>
      <ol className="dw-route-chain">
        {route.map((run, index) => (
          <li key={`${run.agentKey}-${index}`}>
            <span className="dw-chip dw-chip-small dw-chip-dashed"><Icon name="agent" size={14} />{agentName(run.agentKey, t)}</span>
            {index < route.length - 1 && <Icon name="arrow" size={14} />}
          </li>
        ))}
      </ol>
      <dl className="dw-route-steps">
        {route.map((run, index) => (
          <Fragment key={`${run.agentKey}-${index}`}><dt>{agentName(run.agentKey, t)}</dt><dd>{demoText(run.summary)}</dd></Fragment>
        ))}
      </dl>
    </section>
  );
}

/**
 * The Library passages a reply drew on, or a plain statement that it drew on none.
 * @param {object} props
 * @param {object[]} props.sources - One passage per source, each with its title, link and chunk.
 */
function UsedSources({ sources }) {
  const { t, demoText } = useI18n();
  if (!sources.length) return <p className="dw-talk-sources"><Icon name="book" size={16} /><span>{t("noSourcesUsed")}</span></p>;
  return (
    <p className="dw-talk-sources">
      <Icon name="book" size={16} />
      <span>{t("usedFromLibrary")}{" "}
        {sources.map((source, index) => (
          <Fragment key={source.sourceId}>
            {index > 0 && t("listSeparator")}
            {source.sourceUrl ? <a href={source.sourceUrl} target="_blank" rel="noopener noreferrer">{demoText(source.sourceTitle)}</a> : <strong>{demoText(source.sourceTitle)}</strong>}
            {" "}§{source.chunkIndex + 1}
          </Fragment>
        ))}
      </span>
    </p>
  );
}

/**
 * One turn in Talk. The user's words sit on the right; a reply names its mode, says when the local
 * rules answered instead of the model, holds any proposal, and can show its agent route and sources.
 * @param {object} props
 * @param {object} props.message - The message as the local service returns it.
 * @param {boolean} props.demoMode - Whether to translate demo workspace text.
 * @param {React.ReactNode} [props.children] - A proposal made in this reply.
 */
export function TalkMessage({ message, demoMode, children }) {
  const { t, demoText } = useI18n();
  const [shown, setShown] = useState("");
  const routeRef = useRef(null);
  const text = demoMode ? demoText(message.content) : message.content;

  if (message.role === "user") {
    return (
      <div className="dw-talk-user">
        <p>{text}</p>
        {message.voice && <span className="dw-caption"><Icon name="mic" size={14} />{t("voiceTag")}</span>}
      </div>
    );
  }

  const route = message.agentRoute || [];
  const sources = [...new Map((message.retrieval?.matches || []).map((match) => [match.sourceId, match])).values()];
  const toggle = (part) => setShown((current) => (current === part ? "" : part));
  return (
    <article className="dw-talk-reply" aria-label={t("replyLabel", { mode: t(message.mode) })}>
      <p className="dw-talk-who"><span className="dw-talk-avatar"><Icon name="agent" size={16} /></span>DayWright<span className="dw-chip dw-chip-small">{t(message.mode)}</span></p>
      <p className="dw-talk-text">{text}</p>
      {message.model_mode === "rules" && <p className="dw-caption">{t("answeredByRules")}</p>}
      {children}
      {route.length > 0 && (
        <div className="dw-talk-trail">
          <button type="button" className="dw-chip dw-chip-link" ref={routeRef} aria-expanded={shown === "route"} onClick={() => toggle("route")}>
            <Icon name="agent" size={14} />{t("agentsCount", { count: new Set(route.map((run) => run.agentKey)).size })}<Icon name={shown === "route" ? "down" : "right"} size={14} />
          </button>
          <button type="button" className="dw-chip dw-chip-link" aria-expanded={shown === "sources"} onClick={() => toggle("sources")}>
            <Icon name="book" size={14} />{sources.length ? t("sourcesCount", { count: sources.length }) : t("sourcesNone")}<Icon name={shown === "sources" ? "down" : "right"} size={14} />
          </button>
        </div>
      )}
      {shown === "route" && <AgentRoute route={route} onHide={() => { setShown(""); routeRef.current?.focus(); }} />}
      {shown === "sources" && <UsedSources sources={sources} />}
    </article>
  );
}
