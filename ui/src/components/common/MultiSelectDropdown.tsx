import React, { useEffect, useRef, useState } from "react";
import MultiCheckboxSelect, { MultiCheckboxOption } from "./MultiCheckboxSelect";

interface MultiSelectDropdownProps {
  options: MultiCheckboxOption[];
  value: string[];
  onChange: (ids: string[]) => void;
  // Shown on the trigger when nothing is selected.
  placeholder?: string;
  // Shown inside the panel when there are no options to choose from.
  emptyMessage?: string;
  // When true the trigger is disabled and the panel can't be opened.
  disabled?: boolean;
}

// A dropdown wrapper around MultiCheckboxSelect: the trigger summarizes the
// current selection and the checkbox list lives in a popover so the full list
// isn't rendered on screen at all times. Selection stays owned by the parent.
const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  options,
  value,
  onChange,
  placeholder = "Select…",
  emptyMessage = "Nothing to select.",
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close the popover when clicking outside of it.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const selectedLabels = options
    .filter((opt) => value.includes(opt.id))
    .map((opt) => opt.label);

  const summary =
    selectedLabels.length > 0 ? selectedLabels.join(", ") : placeholder;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-md border border-emd-border bg-white text-left text-emd-text focus:outline-none focus:ring-2 focus:ring-emd-primary focus:border-emd-primary transition disabled:bg-emd-accent/10 disabled:text-emd-placeholder disabled:cursor-not-allowed cursor-pointer"
      >
        <span
          className={`truncate ${
            selectedLabels.length > 0 ? "" : "text-emd-placeholder"
          }`}
        >
          {summary}
        </span>
        <span className="shrink-0 text-emd-placeholder">
          {open ? "▲" : "▼"}
        </span>
      </button>

      {open && (
        <div className="absolute z-10 mt-1 w-full rounded-md border border-emd-border bg-white shadow-lg p-2">
          <MultiCheckboxSelect
            options={options}
            value={value}
            onChange={onChange}
            emptyMessage={emptyMessage}
          />
        </div>
      )}
    </div>
  );
};

export default MultiSelectDropdown;
