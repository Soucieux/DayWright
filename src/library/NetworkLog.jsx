import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Sheet } from "../ui/Sheet";
import { clockOfTimestamp, fullDate, localDateOf } from "../time";

/**
 * One request that left this Mac: exactly what was sent, where to, and what came back.
 * @param {object} props
 * @param {{sent: string, destination: string, received: string}} props.entry - A network log entry.
 */
export function NetworkEntry({ entry }) {
  const { t } = useI18n();
  return (
    <span className="dw-network-entry">
      <span>{t("sentWordsTo", { sent: entry.sent, destination: entry.destination })}</span>
      <span className="dw-caption">{t("networkReply", { received: entry.received })}</span>
    </span>
  );
}

/**
 * The network log: every request that has left this Mac, newest first, and what never leaves it.
 * @param {object} props
 * @param {object[]} props.entries - Network log entries, newest first.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function NetworkLogSheet({ entries, onClose }) {
  const { t, language } = useI18n();
  return (
    <Sheet title={t("networkLogTitle")} onClose={onClose}>
      <div className="dw-detail">
        <p className="dw-muted">{t("networkLogIntro")}</p>
        {entries.length ? (
          <ol className="dw-network-log">
            {entries.map((entry) => (
              <li key={entry.id}>
                <span className="dw-caption">{fullDate(localDateOf(entry.happenedAt), language)} · {clockOfTimestamp(entry.happenedAt)}</span>
                <NetworkEntry entry={entry} />
              </li>
            ))}
          </ol>
        ) : <p className="dw-banner dw-banner-history"><Icon name="offline" size={18} />{t("networkLogEmpty")}</p>}
        <p className="dw-ledger-line"><Icon name="offline" size={18} /><span>{t("neverSentLine")}</span></p>
      </div>
    </Sheet>
  );
}
