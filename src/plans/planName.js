/** Message keys for the three kinds of plan the local agents propose. */
const PLAN_NAME_KEYS = { balanced: "planBalanced", focused: "planFocused", gentle: "planGentle" };

/**
 * Name a plan in the interface language.
 * @param {object|undefined} variant - The plan, with its `slug` and stored `name`.
 * @param {(key: string) => string} t - The interface text lookup.
 * @param {(value: string) => string} demoText - Translates demo workspace text.
 * @returns {string} The plan's name, or an empty string when there is no plan.
 */
export function planName(variant, t, demoText) {
  if (!variant) return "";
  const key = PLAN_NAME_KEYS[variant.slug];
  return key ? t(key) : demoText(variant.name);
}
