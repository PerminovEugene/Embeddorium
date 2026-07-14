import React, { useEffect, useState } from "react";
import { useFormContext } from "./FormContext";
import { inputStyle } from "../styles/styles";
import { fetchProviders } from "../api/providers";
import { Provider } from "./providers/types";
import Checkbox from "./common/Checkbox";

// One-line label for the dropdown: name plus the model it serves so the user
// can tell cross-encoders backed by different models apart at a glance.
const providerLabel = (p: Provider): string => {
  const model = p.config.model_name;
  return `${p.name} · ${p.providerType}${model ? ` (${model})` : ""}`;
};

// Hybrid-only: optional cross-encoder reranking of the fused RRF pool. When
// enabled it collects the reranker provider and rerankerTopK the backend needs
// (both required whenever useReranking is true — the server has no default cut
// off). Only cross-encoder providers can rerank, so the dropdown is filtered to
// that model type.
const RerankerControls: React.FC = () => {
  const {
    state,
    setUseReranking,
    setRerankerProviderId,
    setRerankerTopK,
  } = useFormContext();
  const { useReranking, rerankerProviderId, rerankerTopK } = state;

  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProviders = () => {
    setLoading(true);
    setError(null);
    fetchProviders()
      // Only cross-encoder providers can rerank; the backend rejects anything
      // else, so never offer it here.
      .then((all) => all.filter((p) => p.modelType === "cross-encoder"))
      .then((loaded) => {
        setProviders(loaded);
        // Clear the selection if the previously-chosen provider no longer
        // exists in the freshly loaded list.
        if (
          rerankerProviderId &&
          !loaded.some((p) => p.id === rerankerProviderId)
        ) {
          setRerankerProviderId(null);
        }
      })
      .catch((err) => {
        console.error("Failed to load reranker providers:", err);
        setError("Failed to load reranker providers");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadProviders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col" style={{ minWidth: 320 }}>
      <span className="text-sm font-medium text-emd-text mb-1">Reranking</span>
      <div className="py-2">
        <Checkbox
          label="Rerank with cross-encoder"
          checked={useReranking}
          onChange={(e) => setUseReranking(e.target.checked)}
        />
      </div>
      <span className="text-xs text-emd-text">
        Re-scores the fused pool with a cross-encoder, keeping the top results
      </span>

      {useReranking && (
        <div className="flex flex-row flex-wrap items-end gap-4 mt-3">
          <div className="flex flex-col" style={{ minWidth: 260 }}>
            <label className="text-sm font-medium text-emd-text mb-1">
              Reranker provider
            </label>
            <div className="flex flex-row items-center gap-2">
              <select
                style={inputStyle}
                value={rerankerProviderId ?? ""}
                onChange={(e) =>
                  setRerankerProviderId(e.target.value || null)
                }
              >
                <option value="">
                  {loading ? "Loading…" : "Select a cross-encoder"}
                </option>
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {providerLabel(provider)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={loadProviders}
                title="Refresh reranker providers"
                style={{
                  padding: "0.5rem 0.75rem",
                  border: "1px solid #d1d5db",
                  borderRadius: "0.375rem",
                  background: "white",
                  cursor: "pointer",
                }}
              >
                ↻
              </button>
            </div>
            {error && (
              <span className="text-red-500 text-sm mt-1">{error}</span>
            )}
            {!loading && !error && providers.length === 0 && (
              <span className="text-xs text-emd-text mt-1">
                No cross-encoder providers configured
              </span>
            )}
          </div>

          <div className="flex flex-col" style={{ minWidth: 120 }}>
            <label
              className="text-sm font-medium text-emd-text mb-1"
              htmlFor="reranker-top-k"
            >
              Reranker Top K
            </label>
            <input
              id="reranker-top-k"
              type="number"
              min={1}
              step={1}
              style={inputStyle}
              value={rerankerTopK}
              onChange={(e) => setRerankerTopK(e.target.value)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default RerankerControls;
