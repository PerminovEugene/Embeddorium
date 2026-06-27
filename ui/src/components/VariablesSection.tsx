import React from "react";
import VariableGroup from "./VariableGroup";
import { useFormContext } from "./FormContext";
import AddButton from "./AddButton";

interface VariablesSectionProps {
  type: "source" | "candidate";
  validationError?: string;
}

const VariablesSection: React.FC<VariablesSectionProps> = ({ type }) => {
  const { state, addVariableGroup } = useFormContext();
  const groups = state[`${type}VariableGroups`];

  return (
    <div>
      {groups.length > 0 ? (
        groups.map((group, index) => (
          <VariableGroup
            key={group.id}
            groupId={group.id}
            type={type}
            groupIndex={index}
          />
        ))
      ) : (
        <p className="text-sm text-emd-placeholder mb-4">
          No variable groups added yet.
        </p>
      )}

      <div className="mt-4">
        <AddButton
          onClick={() => addVariableGroup(type)}
          text="+ Add Variable Group"
        />
      </div>
    </div>
  );
};

export default VariablesSection;
