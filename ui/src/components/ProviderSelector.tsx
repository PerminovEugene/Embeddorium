import React, { useEffect, useState } from "react";
import { useFormContext } from "./FormContext";
import { inputStyle } from "../styles/styles";
import { fetchProviders } from "../api/providers";
import { Provider } from "./providers/types";

// One-line label for the dropdown: name plus the model it serves so the user
// can tell providers backed by different models apart at a glance.
const providerLabel = (p: Provider): string => {
  if (p.providerType === "ollama") return `${p.name} · ollama (${p.modelName})`;
  if (p.providerType === "remote") return `${p.name} · remote (${p.modelName})`;
  return `${p.name} · mock`;
};

// Replaces the manual Ollama-port + model-name inputs in compare mode: the user
// picks a saved provider instead, and its type/model/port are resolved
// server-side from the id we send.
const ProviderSelector: React.FC = () => {
  const { state, setSelectedProvider } = useFormContext();
  const { selectedProvider } = state;

  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProviders = () => {
    setLoading(true);
    setError(null);
    fetchProviders()
      // Only embedding providers make sense here — compare scores embeddings.
      .then((all) => all.filter((p) => p.modelType === "embedding"))
      .then((loaded) => {
        setProviders(loaded);
        // Re-sync the selected provider with the freshly loaded list (its
        // config may have changed), or clear it if it no longer exists.
        if (selectedProvider) {
          setSelectedProvider(
            loaded.find((p) => p.id === selectedProvider.id) ?? null
          );
        }
      })
      .catch((err) => {
        console.error("Failed to load providers:", err);
        setError("Failed to load providers");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadProviders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const provider = providers.find((p) => p.id === e.target.value) ?? null;
    setSelectedProvider(provider);
  };

  return (
    <div className="flex flex-col mr-5" style={{ minWidth: 320 }}>
      <label className="text-sm font-medium text-emd-text mb-1">Provider</label>
      <div className="flex flex-row items-center gap-2">
        <select
          style={inputStyle}
          value={selectedProvider?.id ?? ""}
          onChange={handleChange}
        >
          <option value="">
            {loading ? "Loading…" : "Select a provider"}
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
          title="Refresh providers"
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
      {error && <span className="text-red-500 text-sm mt-1">{error}</span>}
    </div>
  );
};

export default ProviderSelector;
