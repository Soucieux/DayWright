import { useI18n } from "../i18n";
import { PLAN_TYPES } from "./planName";

/**
 * Every kind of plan the agents can propose, so the user knows what each one does and when it is
 * offered before comparing the day's three.
 */
export function PlanTypes() {
  const { t } = useI18n();
  return (
    <div className="dw-plan-types">
      <p className="dw-caption">{t("planTypesIntro")}</p>
      <ul>
        {PLAN_TYPES.map((type) => (
          <li key={type.slug}>
            <strong>{t(type.name)}</strong>
            <span>{t(type.tagline)}</span>
            <span className="dw-caption">{t(type.when)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
