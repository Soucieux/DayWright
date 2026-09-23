import { useI18n } from "../i18n";
import { Icon } from "./Icon";

/** The design's area for each stored domain. */
const AREA_OF_DOMAIN = { learning: "learn", life: "life", finance: "money", rest: "rest" };

/**
 * Map a stored domain to its design area.
 * @param {string} domain - `learning`, `life`, `finance` or `rest`.
 * @returns {string|undefined} `learn`, `life`, `money` or `rest`; undefined for anything else.
 */
export function areaOf(domain) {
  return AREA_OF_DOMAIN[domain];
}

/**
 * Name an area with its glyph, its label and its colour together, so colour is never the only signal.
 * A domain outside the four areas, such as cross-area advice, shows its label alone.
 * @param {object} props
 * @param {string} props.domain - The stored domain.
 * @param {boolean} [props.plain=false] - Glyph and label without the tinted chip.
 */
export function AreaTag({ domain, plain = false }) {
  const { t } = useI18n();
  const area = areaOf(domain);
  if (!area) return <span className="dw-area-tag dw-area-none">{t(domain)}</span>;
  return (
    <span className={`dw-area-tag dw-area-${area}${plain ? " dw-area-plain" : ""}`}>
      <Icon name={`area-${area}`} size={12} />{t(domain)}
    </span>
  );
}

/**
 * An area's glyph alone, for compact rows. Its shape tells the areas apart without colour, and its
 * label is still spoken.
 * @param {object} props
 * @param {string} props.domain - The stored domain.
 */
export function AreaGlyph({ domain }) {
  const { t } = useI18n();
  const area = areaOf(domain);
  if (!area) return null;
  return <span className={`dw-area-glyph dw-area-${area}`}><Icon name={`area-${area}`} size={12} label={t(domain)} /></span>;
}
