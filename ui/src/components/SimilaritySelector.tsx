// SimilaritySelector.tsx
import React from "react";
import { useFormContext } from "./FormContext";
import { Similarity, options } from "./consts";

const SimilaritySelector: React.FC = () => {
  const toggle = (id: Similarity) => {
    checkSimilarity(id);
  };

  const { state, checkSimilarity } = useFormContext();
  const { similarities } = state;
  console.log("options ->", options);
  return (
    <div className="flex flex-col gap-2">
      <span>Similarity type</span>

      <div className="flex flex-col gap-2">
        {options.map(({ id, label }) => (
          <label
            key={id}
            id={id}
            className="flex items-center gap-2 text-sm text-emd-text"
          >
            <input
              type="checkbox"
              checked={similarities.includes(id)}
              onChange={() => toggle(id)}
              className="accent-emd-primary w-4 h-4"
            />
            <span> {label}</span>
          </label>
        ))}
      </div>
    </div>
  );
};

export default SimilaritySelector;
