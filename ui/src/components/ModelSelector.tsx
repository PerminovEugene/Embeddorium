import React from "react";
import { inputStyle } from "../styles/styles";
import { useFormContext } from "./FormContext";
import AddButton from "./AddButton";
import RemoveButton from "./RemoveButton";

const MAX_MODELS = 5;

const ModelSelector: React.FC = () => {
  const { state, addModel, removeModel, updateModel } = useFormContext();
  const { models } = state;

  return (
    <div style={{ marginBottom: "2rem" }}>
      <span style={{ display: "block", marginBottom: "0.75rem" }}>
        Model names
      </span>

      {models.map((model, index) => (
        <div
          key={model.id}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "0.5rem",
          }}
        >
          <input
            type="text"
            placeholder={`Model ${index + 1}`}
            value={model.name}
            onChange={(e) => updateModel(model.id, e.target.value)}
            style={{ ...inputStyle }}
          />
          {models.length > 1 && (
            // <button
            //   className="px-3 py-2 text-sm rounded border-none bg-red-400 text-white hover:bg-red-500 transition"
            //   onClick={() => removeModel(model.id)}
            // >
            //   Remove
            // </button>
            <RemoveButton onClick={() => removeModel(model.id)} text="Remove" />
          )}
        </div>
      ))}

      {models.length < MAX_MODELS && (
        <AddButton onClick={addModel} text="+ Add Model" />
      )}
    </div>
  );
};

export default ModelSelector;
