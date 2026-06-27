import React from "react";
import { useFormContext } from "./FormContext";
import { inputStyle } from "../styles/styles";

const OllamaPortInput: React.FC = () => {
  const { state, changeOllamaPort } = useFormContext();
  const { ollamaPort } = state;

  return (
    <div className="flex flex-col mr-5">
      <label
        htmlFor="embeddingModelInput"
        className="text-sm font-medium text-emd-text mb-1"
      >
        Ollama Port
      </label>
      <input
        type="number"
        id="embeddingModelInput"
        style={inputStyle}
        value={ollamaPort}
        onChange={(e) => changeOllamaPort(e.target.value)}
        placeholder="11434"
      />
    </div>
  );
};

export default OllamaPortInput;
