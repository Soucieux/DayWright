/**
 * A row of mutually exclusive choices, shown all at once.
 * @param {object} props
 * @param {string} props.label - The group's accessible name.
 * @param {[string, React.ReactNode][]} props.options - Each option's value and content.
 * @param {string} props.value - The chosen value.
 * @param {(value: string) => void} props.onChange - Choose a value.
 * @param {string} [props.className] - Extra classes for the group.
 */
export function Segmented({ label, options, value, onChange, className = "" }) {
  return (
    <div className={`dw-segmented ${className}`.trim()} role="radiogroup" aria-label={label}>
      {options.map(([option, content]) => (
        <button key={option} type="button" role="radio" aria-checked={value === option} onClick={() => onChange(option)}>{content}</button>
      ))}
    </div>
  );
}
