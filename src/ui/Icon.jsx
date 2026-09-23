const sources = import.meta.glob("../../design/icons/*.svg", { query: "?raw", import: "default", eager: true });

/** Every design icon's markup, keyed by its file name without `.svg`. */
const ICONS = Object.fromEntries(
  Object.entries(sources).map(([path, markup]) => [path.slice(path.lastIndexOf("/") + 1, -4), markup]),
);

/**
 * Draw one of the design's 24-pixel icons inline, so it takes the surrounding text colour.
 * @param {object} props
 * @param {string} props.name - The icon's file name in `design/icons`, without `.svg`.
 * @param {number} [props.size=20] - The rendered width and height in pixels.
 * @param {string} [props.label] - An accessible name; without one the icon is decorative.
 * @returns {JSX.Element|null} The icon, or nothing when no icon has that name.
 */
export function Icon({ name, size = 20, label }) {
  const markup = ICONS[name];
  if (!markup) return null;
  const sized = markup.replace('width="24" height="24"', `width="${size}" height="${size}"`);
  return (
    <span
      className="dw-icon"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : "true"}
      dangerouslySetInnerHTML={{ __html: sized }}
    />
  );
}
