import { createContext, useContext } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { needsLine, openSettings } from "./models";

/**
 * The models states the local service gives with each day, whether Ava answers now (see avaOn), and whether the
 * local service answered at all; App provides them, so any place that needs a model can say so without each screen
 * passing them down. Without the service nothing is said about models: the offline view says why.
 */
export const ModelsContext = createContext({ models: undefined, ava: false, connected: false });

/**
 * What a feature says in its own place while its model isn't ready: what it needs and why, with Open Settings.
 * @param {object} props
 * @param {string} props.feature - The key of its first sentence, such as `searchNeedsModel`.
 * @param {"chat"|"embedding"|"speech"} props.role - The model it needs.
 */
export function NeedsModel({ feature, role }) {
  const { t, language } = useI18n();
  const { models } = useContext(ModelsContext);
  return (
    <p className="dw-needs-model" role="note">
      <Icon name="alert" size={16} />
      <span>{needsLine(feature, models, role, t, language)}</span>
      <button type="button" className="dw-link" onClick={openSettings}>{t("openSettings")}</button>
    </p>
  );
}

/**
 * A control that asks Ava for something: on show while Ava answers; while the service answers but she can't, the
 * line saying she needs a local model, with Open Settings, in its place, so nothing sends the user to Ava for what
 * she can't do now. Without the service the control stays, as the offline view has it.
 * @param {object} props
 * @param {React.ReactNode} props.children - The control.
 */
export function AvaOnly({ children }) {
  const { ava, connected } = useContext(ModelsContext);
  return connected && !ava ? <NeedsModel feature="avaNeedsModel" role="chat" /> : children;
}
