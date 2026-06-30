import React from "react";
import ScrollableList from "../common/ScrollableList";
import { Provider } from "./types";

interface ProviderListProps {
  providers: Provider[];
  selectedId: string | null;
  onSelect: (provider: Provider) => void;
  loading?: boolean;
}

// Human-readable label for the provider type chip.
const PROVIDER_TYPE_LABELS: Record<Provider["providerType"], string> = {
  ollama: "Local Ollama",
  remote: "Remote",
  mock: "Mock",
};

// Provider-specific binding of the generic ScrollableList.
const ProviderList: React.FC<ProviderListProps> = ({
  providers,
  selectedId,
  onSelect,
  loading,
}) => {
  if (loading) {
    return <p className="text-emd-placeholder text-sm p-3">Loading…</p>;
  }

  return (
    <ScrollableList<Provider>
      items={providers}
      getKey={(p) => p.id}
      selectedKey={selectedId}
      onSelect={onSelect}
      emptyMessage="No providers yet."
      className="max-h-[60vh]"
      renderItem={(p) => (
        <div className="flex flex-col">
          <span className="font-medium">{p.name}</span>
          <span className="text-xs opacity-70 uppercase tracking-wide">
            {PROVIDER_TYPE_LABELS[p.providerType]} · {p.modelType}
          </span>
        </div>
      )}
    />
  );
};

export default ProviderList;
