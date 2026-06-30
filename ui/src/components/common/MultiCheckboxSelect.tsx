import React from "react";

export interface MultiCheckboxOption {
  id: string;
  label: string;
  // Optional secondary line (e.g. a type chip).
  sublabel?: string;
}

interface MultiCheckboxSelectProps {
  options: MultiCheckboxOption[];
  value: string[];
  onChange: (ids: string[]) => void;
  emptyMessage?: string;
  // When true the selection is shown read-only — checkboxes can't be toggled.
  disabled?: boolean;
}

// A controlled list of checkboxes for picking many of `options`. Selection is
// owned by the parent. Used for choosing the providers and datasets a pipeline
// uses.
const MultiCheckboxSelect: React.FC<MultiCheckboxSelectProps> = ({
  options,
  value,
  onChange,
  emptyMessage = "Nothing to select.",
  disabled = false,
}) => {
  if (options.length === 0) {
    return <p className="text-emd-placeholder text-sm">{emptyMessage}</p>;
  }

  const toggle = (id: string) =>
    onChange(
      value.includes(id) ? value.filter((v) => v !== id) : [...value, id]
    );

  return (
    <ul className="flex flex-col gap-1 max-h-52 overflow-y-auto">
      {options.map((opt) => (
        <li key={opt.id}>
          <label
            className={`flex items-start gap-2 px-2 py-1 rounded-md text-sm text-emd-text transition-colors ${
              disabled
                ? "cursor-not-allowed opacity-60"
                : "cursor-pointer hover:bg-emd-accent/20"
            }`}
          >
            <input
              type="checkbox"
              checked={value.includes(opt.id)}
              onChange={() => toggle(opt.id)}
              disabled={disabled}
              className="accent-emd-primary w-4 h-4 mt-0.5 disabled:cursor-not-allowed"
            />
            <span className="flex flex-col">
              <span className="font-medium">{opt.label}</span>
              {opt.sublabel && (
                <span className="text-xs opacity-70 uppercase tracking-wide">
                  {opt.sublabel}
                </span>
              )}
            </span>
          </label>
        </li>
      ))}
    </ul>
  );
};

export default MultiCheckboxSelect;
