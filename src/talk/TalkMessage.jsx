import { Fragment, useRef, useState } from "react";
import guide from "../guide/guide.json";
import { seeGuide } from "../guide/guideCards";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { agentName, agentRole } from "../ui/agentName";
import { noticeText } from "./notices";
import { textRuns } from "./richText";

/**
 * The agents that worked on a reply, in order: each one's job in a line, then what it did.
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
            <span className="dw-chip dw-chip-small dw-chip-dashed"><Icon name="agent" size={14} />{agentName(run.agentKey, t, run.phase)}</span>
            {index < route.length - 1 && <Icon name="arrow" size={14} />}
          </li>
        ))}
      </ol>
      <dl className="dw-route-steps">
        {route.map((run, index) => (
          <Fragment key={`${run.agentKey}-${index}`}>
            <dt>{agentName(run.agentKey, t, run.phase)}</dt>
            <dd>{agentRole(run.agentKey, t) && <span className="dw-agent-role">{agentRole(run.agentKey, t)}</span>}{demoText(run.summary)}</dd>
          </Fragment>
        ))}
      </dl>
    </section>
  );
}

/**
 * The Library passages a reply drew on, or a plain statement that it drew on none.
 * @param {object} props
 * @param {object[]} props.used - One passage per note or file, each with its title and part.
 */
function UsedPassages({ used }) {
  const { t, demoText } = useI18n();
  if (!used.length) return <p className="dw-talk-sources"><Icon name="book" size={16} /><span>{t("libraryNoneUsed")}</span></p>;
  return (
    <p className="dw-talk-sources">
      <Icon name="book" size={16} />
      <span>{t("usedFromLibrary")}{" "}
        {used.map((match, index) => (
          <Fragment key={match.sourceId}>
            {index > 0 && t("listSeparator")}
            <strong>{demoText(match.sourceTitle)}</strong>{" "}§{match.chunkIndex + 1}
          </Fragment>
        ))}
      </span>
    </p>
  );
}

/**
 * A message Ava posted about an issue an agent found, under Ava's avatar, naming the agent in a
 * dashed chip as everything agents raise does.
 * @param {object} props
 * @param {object} props.notice - The message as the local service returns it; see notices.js.
 * @param {boolean} props.demoMode - Whether to translate demo workspace task titles.
 */
export function TalkNotice({ notice, demoMode }) {
  const { t, language, demoText } = useI18n();
  const from = t("avaNoticeFrom", { agent: agentName(notice.agentKey, t) });
  return (
    <article className="dw-talk-reply" aria-label={from}>
      <p className="dw-talk-who"><span className="dw-talk-avatar"><Icon name="agent" size={16} /></span>
        <span className="dw-chip dw-chip-small dw-chip-dashed">{from}</span></p>
      <p className="dw-talk-text">{noticeText(notice, t, language, demoMode ? demoText : undefined)}</p>
    </article>
  );
}

/** What Ava understood a message to be, by the mode the service worked out. */
const MODE_KEYS = { ask: "avaModeAsk", adjust: "avaModeAdjust", report: "avaModeReport" };

/**
 * One turn with Ava. The user's words sit on the right; a reply, under Ava's avatar rather than its
 * name, which the window's title already shows, says what Ava understood the message to be, says
 * when the local rules answered instead of the model, holds any proposal, and can show its agent
 * route and the Library passages it drew on. An answer from the Guide's cards, in English like the
 * Guide, ends with a link to each card.
 * @param {object} props
 * @param {object} props.message - The message as the local service returns it.
 * @param {boolean} props.demoMode - Whether to translate demo workspace text.
 * @param {(card: string) => void} props.onGuide - Show a card in the Guide.
 * @param {React.ReactNode} [props.children] - A proposal made in this reply.
 */
export function TalkMessage({ message, demoMode, onGuide, children }) {
  const { t, demoText } = useI18n();
  const [shown, setShown] = useState("");
  const routeRef = useRef(null);
  const fromGuide = message.model_mode === "guide";
  const { text, cards } = fromGuide ? seeGuide(guide, message.content)
    : { text: demoMode ? demoText(message.content) : message.content, cards: [] };

  if (message.role === "user") {
    return <div className="dw-talk-user"><p>{text}</p></div>;
  }

  const route = message.agentRoute || [];
  const used = [...new Map((message.retrieval?.matches || []).map((match) => [match.sourceId, match])).values()];
  const toggle = (part) => setShown((current) => (current === part ? "" : part));
  return (
    <article className="dw-talk-reply" aria-label={t("replyLabel", { mode: t(MODE_KEYS[message.mode] || "avaModeAsk") })}>
      <p className="dw-talk-who"><span className="dw-talk-avatar"><Icon name="agent" size={16} /></span>
        <span className="dw-chip dw-chip-small">{t(MODE_KEYS[message.mode] || "avaModeAsk")}</span></p>
      <p className="dw-talk-text" lang={fromGuide ? "en" : undefined}>{textRuns(text).map((run, index) => (run.strong && run.em ? <strong key={index}><em>{run.text}</em></strong>
        : run.strong ? <strong key={index}>{run.text}</strong>
          : run.em ? <em key={index}>{run.text}</em> : <Fragment key={index}>{run.text}</Fragment>))}</p>
      {cards.length > 0 && (
        <p className="dw-talk-see-guide" lang="en">{guide.labels.seeGuide}:{" "}
          {cards.map((card, index) => (
            <Fragment key={card.id}>
              {index > 0 && ", "}<button type="button" className="dw-link" onClick={() => onGuide(card.id)}>{card.title}</button>
            </Fragment>
          ))}
        </p>
      )}
      {message.model_mode === "rules" && <p className="dw-caption">{t("answeredByRules")}</p>}
      {children}
      {route.length > 0 && (
        <div className="dw-talk-trail">
          <button type="button" className="dw-chip dw-chip-link" ref={routeRef} aria-expanded={shown === "route"} onClick={() => toggle("route")}>
            <Icon name="agent" size={14} />{t("agentsCount", { count: new Set(route.map((run) => run.agentKey)).size })}<Icon name={shown === "route" ? "down" : "right"} size={14} />
          </button>
          <button type="button" className="dw-chip dw-chip-link" aria-expanded={shown === "library"} onClick={() => toggle("library")}>
            <Icon name="book" size={14} />{used.length ? t("libraryUsedCount", { count: used.length }) : t("libraryUsedNone")}<Icon name={shown === "library" ? "down" : "right"} size={14} />
          </button>
        </div>
      )}
      {shown === "route" && <AgentRoute route={route} onHide={() => { setShown(""); routeRef.current?.focus(); }} />}
      {shown === "library" && <UsedPassages used={used} />}
    </article>
  );
}
