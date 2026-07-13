import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
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
//
// The panel is rendered in a portal with fixed positioning so it can extend
// past the bottom of any `overflow-hidden` ancestor (e.g. a Card) instead of
// being clipped.
const MultiSelectDropdown: React.FC<MultiSelectDropdownProps> = ({
  options,
  value,
  onChange,
  placeholder = "Select…",
  emptyMessage = "Nothing to select.",
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [panelStyle, setPanelStyle] = useState<React.CSSProperties>({});

  // Position the fixed panel just below the trigger, matching its width.
  useLayoutEffect(() => {
    if (!open) return;
    const updatePosition = () => {
      const trigger = triggerRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      setPanelStyle({
        position: "fixed",
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
      });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    // Capture-phase so we reposition on scrolls of any ancestor container.
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  // Close the popover when clicking outside of both the trigger and the panel.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        panelRef.current?.contains(target)
      ) {
        return;
      }
      setOpen(false);
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
    <div className="relative">
      <button
        ref={triggerRef}
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

      {open &&
        createPortal(
          <div
            ref={panelRef}
            style={panelStyle}
            className="z-50 rounded-md border border-emd-border bg-white shadow-lg p-2"
          >
            <MultiCheckboxSelect
              options={options}
              value={value}
              onChange={onChange}
              emptyMessage={emptyMessage}
            />
          </div>,
          document.body,
        )}
    </div>
  );
};

export default MultiSelectDropdown;
