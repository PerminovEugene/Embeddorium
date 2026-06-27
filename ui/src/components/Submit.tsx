import { useState } from "react";
import { substituteVariables } from "../utils/helpers";
import { useFormContext } from "./FormContext";
import { Match } from "./types";
import { sectionStyle } from "../styles/styles";

export const inputIdGroupSeparator = "____";

const SubmitButton = () => {
  const [errors, setErrors] = useState<string[]>([]);

  const { state, validate, setMatches, saveFormToStorage } = useFormContext();

  const validateForm = (): boolean => {
    const errors = validate();
    setErrors(errors);
    return errors.length === 0;
  };

  const handleCompare = () => {
    if (!validateForm()) return;

    const processedSourceInputs = state.sourceInputs
      .map((input) =>
        state.sourceVariableGroups.length
          ? state.sourceVariableGroups.map((group) => ({
              id: input.id + inputIdGroupSeparator + group.id,
              text: substituteVariables(input.text, group.variables),
            }))
          : { id: input.id, text: input.text }
      )
      .flat();

    const processedCandidateInputs = state.candidateInputs
      .map((input) =>
        state.candidateVariableGroups.length
          ? state.candidateVariableGroups.map((group) => ({
              id: input.id + inputIdGroupSeparator + group.id,
              text: substituteVariables(input.text, group.variables),
            }))
          : { id: input.id, text: input.text }
      )
      .flat();

    const data = {
      configuration: {
        ollamaPort: state.ollamaPort,
        modelNames: state.models.map((model) => model.name),
        similarities: state.similarities,
      },
      source: { inputs: processedSourceInputs },
      candidates: { inputs: processedCandidateInputs },
    };

    fetch("http://localhost:8000/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })
      .then((res) => res.json())
      .then((result) => {
        saveFormToStorage();
        const enrichedMatches = result.matches.map((match: Match) => {
          const sourceText = processedSourceInputs.find(
            (input) => input.id === match.source_id
          )?.text;
          const candidateText = processedCandidateInputs.find(
            (input) => input.id === match.candidate_id
          )?.text;
          return { ...match, sourceText, candidateText };
        });
        setMatches(enrichedMatches);
      })
      .catch((error) => {
        console.error("Error sending data to server:", error);
      });
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        marginBottom: "1.5rem",
      }}
      className="flex flex-col justify-around items-center"
    >
      <div className="flex flex-row">
        {errors.length && (
          <section style={sectionStyle} className="bg-emd-panel">
            {errors.map((error, index) => (
              <div key={error + index} className="text-red-500">
                {error}
              </div>
            ))}
          </section>
        )}
      </div>

      <button
        onClick={handleCompare}
        style={{
          padding: "0.75rem 2rem",
          backgroundColor: "#10b981",
          color: "white",
          borderRadius: "0.375rem",
          border: "none",
          fontWeight: "600",
          cursor: "pointer",
        }}
      >
        Compare
      </button>
    </div>
  );
};

export default SubmitButton;
