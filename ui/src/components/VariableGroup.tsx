import React from "react";
import { useFormContext } from "./FormContext";
import AddButton from "./AddButton";
import RemoveButton from "./RemoveButton";

interface VariableGroupProps {
  groupId: string;
  type: "source" | "candidate";
  groupIndex: number;
}

const VariableGroup: React.FC<VariableGroupProps> = ({
  groupId,
  type,
  groupIndex,
}) => {
  const { state, addVariable, removeVariable, updateVariable } =
    useFormContext();
  const group = state[`${type}VariableGroups`].find((g) => g.id === groupId);

  if (!group) return null;

  return (
    <div className="mb-6 p-4 border border-emd-border rounded-md bg-emd-panel shadow-sm">
      <span className="block mb-3 text-sm font-semibold text-emd-text">
        Variable Group {groupIndex}
      </span>

      {group.variables.map((variable, index) => (
        <div key={variable.id} className="flex items-center gap-2 mb-2">
          <input
            type="text"
            value={variable.input}
            onChange={(e) =>
              updateVariable(type, groupId, variable.id, e.target.value)
            }
            placeholder={`{{${index}}}`}
            className="flex-1 p-2 rounded-md border border-emd-border bg-white text-emd-text placeholder-emd-placeholder focus:outline-none focus:ring-2 focus:ring-emd-primary"
          />
          {/* <button
            onClick={() => removeVariable(type, groupId, variable.id)}
            className="px-3 py-2 text-sm rounded-md bg-red-300 text-white hover:bg-red-500 transition-all max-h-12"
          >
            Remove
          </button> */}
          <RemoveButton
            onClick={() => removeVariable(type, groupId, variable.id)}
            text="Remove"
          />
        </div>
      ))}

      <div className="mt-4">
        <AddButton
          onClick={() => addVariable(type, groupId)}
          text="+ Add Variable"
        />
      </div>
    </div>
  );
};

export default VariableGroup;
