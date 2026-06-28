import React from "react";
import { useFormContext } from "./FormContext";
import { SourceType } from "./types";

const modes: { id: SourceType; label: string }[] = [
  { id: "manual", label: "Compare inputs" },
  { id: "db", label: "Search vector DB" },
];

const SourceModeSelector: React.FC = () => {
  const { state, setSourceType } = useFormContext();
  const { sourceType } = state;

  return (
    <div className="flex flex-col gap-2 mr-5">
      <span>Source</span>
      <div className="flex flex-row gap-4">
        {modes.map(({ id, label }) => (
          <label
            key={id}
            className="flex items-center gap-2 text-sm text-emd-text cursor-pointer"
          >
            <input
              type="radio"
              name="sourceType"
              checked={sourceType === id}
              onChange={() => setSourceType(id)}
              className="accent-emd-primary w-4 h-4"
            />
            <span>{label}</span>
          </label>
        ))}
      </div>
    </div>
  );
};

export default SourceModeSelector;
