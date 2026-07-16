import { useState } from "react";
import { substituteVariables } from "../utils/helpers";
import { useFormContext } from "./FormContext";
import { Match, DbMatch } from "./types";
import { SERVER_URL } from "./consts";
import { sectionStyle } from "../styles/styles";

export const inputIdGroupSeparator = "____";

// Read the server's error message from a failed response. The API returns
// `{ "detail": "..." }` (FastAPI's HTTPException shape); fall back to the status
// code when there's no JSON body.
async function readErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch {
    // no JSON body to read
  }
  return `Request failed (${res.status})`;
}

const SubmitButton = () => {
  const [errors, setErrors] = useState<string[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);

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

  const handleSearch = async () => {
    if (!validateForm()) return;
    setServerError(null);

    const processedSourceInputs = buildProcessedSourceInputs();

    // Cross-encoder reranking is hybrid-only and opt-in; only send its fields
    // when both apply so non-hybrid searches keep a clean configuration and the
    // backend never sees stray reranker params.
    const rerankerConfig =
      state.searchMethod === "hybrid" && state.useReranking
        ? {
            useReranking: true,
            rerankerProviderId: state.rerankerProviderId,
            rerankerTopK: Number(state.rerankerTopK),
          }
        : {};

    const data = {
      configuration: {
        // The run supplies the collection + embedding model server-side.
        runId: state.selectedRun?.id,
        // How many results to return per query.
        topK: Number(state.topK),
        // How queries are matched: semantic (vectors), keyword (BM25) or
        // hybrid (both fused via reciprocal rank fusion).
        searchMethod: state.searchMethod,
        // Whether to persist this launch to the search history.
        saveResults: state.saveResults,
        // Optional cross-encoder reranking (hybrid only).
        ...rerankerConfig,
      },
      source: { inputs: processedSourceInputs },
    };

    setLoading(true);
    try {
      const res = await fetch(`${SERVER_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));

      const result = await res.json();
      saveFormToStorage();
      const dbMatches: DbMatch[] = (result.results ?? []).map((hit: DbMatch) => {
        const queryText = processedSourceInputs.find(
          (input) => input.id === hit.source_id
        )?.text;
        return { ...hit, queryText: queryText ?? hit.queryText };
      });
      setDbMatches(dbMatches);
    } catch (error) {
      console.error("Error searching collection:", error);
      setDbMatches([]);
      setServerError(error instanceof Error ? error.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (state.sourceType === "db") {
      handleSearch();
      return;
    }

    if (!validateForm()) return;
    setServerError(null);

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
    try {
      const res = await fetch(`${SERVER_URL}/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));

      const result = await res.json();
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
    } catch (error) {
      console.error("Error sending data to server:", error);
      setMatches([]);
      setServerError(
        error instanceof Error ? error.message : "Comparison failed"
      );
    } finally {
      setLoading(false);
    }
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
        {(errors.length > 0 || serverError) && (
          <section style={sectionStyle} className="bg-emd-panel">
            {errors.map((error, index) => (
              <div key={error + index} className="text-red-500">
                {error}
              </div>
            ))}
            {serverError && <div className="text-red-500">{serverError}</div>}
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
