import { readFileSync } from "node:fs";

/**
 * The interface's text in both languages, read from i18n.jsx, which node can't import as it holds JSX.
 * @returns {{en: Record<string, string>, zh: Record<string, string>}} Each language's messages by key.
 */
export function interfaceText() {
  const source = readFileSync(new URL("../src/i18n.jsx", import.meta.url), "utf8");
  const opening = "const messages = ";
  const start = source.indexOf(opening) + opening.length;
  return new Function(`return ${source.slice(start, source.indexOf("\n};\n", start) + 2)}`)();
}
