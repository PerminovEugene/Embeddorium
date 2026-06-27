import React from "react";
import { useFormContext } from "./FormContext";
import AddButton from "./AddButton";
import RemoveButton from "./RemoveButton";

interface InputsSectionProps {
  type: "source" | "candidate";
  validationError?: string;
}

const InputsSection: React.FC<InputsSectionProps> = ({ type }) => {
  const { state, addInput, removeInput, updateInput } = useFormContext();
  const groups = state[`${type}Inputs`];

  return (
    <div>
      <hr className="border-t border-emd-border my-6" />

      {groups.map((group, index) => (
        <div key={group.id} className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <p className="text-sm font-semibold text-emd-text m-0">
              Input {index}
            </p>
          </div>
          <div className="flex flex-row items-start gap-2">
            <textarea
              id={`group-${group.id}`}
              rows={2}
              value={group.text}
              onChange={(e) => updateInput(type, group.id, e.target.value)}
              placeholder="Enter input..."
              className="flex-1 p-2 rounded-md border border-emd-border bg-white text-emd-text placeholder-emd-placeholder focus:outline-none focus:ring-2 focus:ring-emd-primary min-h-[3rem]"
            />
            {groups.length > 1 && (
              <RemoveButton
                onClick={() => removeInput(type, group.id)}
                text="Remove"
              />
            )}
          </div>
        </div>
      ))}

      <div className="mt-4">
        <AddButton onClick={() => addInput(type)} text="+ Add Input" />
      </div>
    </div>
  );
};

export default InputsSection;
