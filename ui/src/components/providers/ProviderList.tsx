import React from "react";
import ScrollableList from "../common/ScrollableList";
import { Provider, ProviderTypeConfig } from "./types";

interface ProviderListProps {
  providers: Provider[];
  providerConfigs: ProviderTypeConfig[];
  selectedId: string | null;
  onSelect: (provider: Provider) => void;
  loading?: boolean;
}

// Provider-specific binding of the generic ScrollableList.
const ProviderList: React.FC<ProviderListProps> = ({
  providers,
  providerConfigs,
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
            {providerConfigs.find((config) => config.name === p.providerType)?.label ??
              p.providerType} · {p.modelType}
          </span>
        </div>
      )}
    />
  );
};

export default ProviderList;
