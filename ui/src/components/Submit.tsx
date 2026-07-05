import { useState } from "react";
import { substituteVariables } from "../utils/helpers";
import { useFormContext } from "./FormContext";
import { Match, DbMatch } from "./types";
import { SERVER_URL } from "./consts";
import { sectionStyle } from "../styles/styles";

export const inputIdGroupSeparator = "____";

const SubmitButton = () => {
  const [errors, setErrors] = useState<string[]>([]);

  const {
    state,
    loading,
    setLoading,
    validate,
    setMatches,
    setDbMatches,
    saveFormToStorage,
  } = useFormContext();

  const validateForm = (): boolean => {
    const errors = validate();
    setErrors(errors);
    return errors.length === 0;
  };

  const buildProcessedSourceInputs = () =>
    state.sourceInputs
      .map((input) =>
        state.sourceVariableGroups.length
          ? state.sourceVariableGroups.map((group) => ({
              id: input.id + inputIdGroupSeparator + group.id,
              text: substituteVariables(input.text, group.variables),
            }))
          : { id: input.id, text: input.text }
      )
      .flat();

  const handleSearch = () => {
    if (!validateForm()) return;

    const processedSourceInputs = buildProcessedSourceInputs();

    const data = {
      configuration: {
        ollamaPort: state.ollamaPort,
        // The run supplies the collection + embedding model server-side.
        runId: state.selectedRun?.id,
      },
      source: { inputs: processedSourceInputs },
    };

    setLoading(true);
    fetch(`${SERVER_URL}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })
      .then((res) => res.json())
      .then((result) => {
        saveFormToStorage();
        const dbMatches: DbMatch[] = (result.results ?? []).map(
          (hit: DbMatch) => {
            const queryText = processedSourceInputs.find(
              (input) => input.id === hit.source_id
            )?.text;
            return { ...hit, queryText: queryText ?? hit.queryText };
          }
        );
        setDbMatches(dbMatches);
      })
      .catch((error) => {
        console.error("Error searching collection:", error);
      })
      .finally(() => setLoading(false));
  };

  const handleCompare = () => {
    if (state.sourceType === "db") {
      handleSearch();
      return;
    }

    if (!validateForm()) return;

    const processedSourceInputs = buildProcessedSourceInputs();

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
        // The provider supplies the embedding type/model/port server-side.
        providerId: state.selectedProvider?.id,
        similarities: state.similarities,
      },
      source: { inputs: processedSourceInputs },
      candidates: { inputs: processedCandidateInputs },
    };

    setLoading(true);
    fetch(`${SERVER_URL}/compare`, {
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
      })
      .finally(() => setLoading(false));
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
        disabled={loading}
        style={{
          padding: "0.75rem 2rem",
          backgroundColor: loading ? "#6ee7b7" : "#10b981",
          color: "white",
          borderRadius: "0.375rem",
          border: "none",
          fontWeight: "600",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Searching…" : "Search"}
      </button>
    </div>
  );
};

export default SubmitButton;
