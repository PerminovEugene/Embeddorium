import React from "react";
import ScrollableList from "../common/ScrollableList";
import { Dataset } from "./types";

interface DatasetListProps {
  datasets: Dataset[];
  selectedId: string | null;
  onSelect: (dataset: Dataset) => void;
  loading?: boolean;
}

// Dataset-specific binding of the generic ScrollableList.
const DatasetList: React.FC<DatasetListProps> = ({
  datasets,
  selectedId,
  onSelect,
  loading,
}) => {
  if (loading) {
    return <p className="text-emd-placeholder text-sm p-3">Loading…</p>;
  }

  return (
    <ScrollableList<Dataset>
      items={datasets}
      getKey={(d) => d.id}
      selectedKey={selectedId}
      onSelect={onSelect}
      emptyMessage="No datasets yet."
      className="max-h-[60vh]"
      renderItem={(d) => (
        <div className="flex flex-col">
          <span className="font-medium">{d.name}</span>
          <span className="text-xs opacity-70 uppercase tracking-wide">
            {d.sourceType}
          </span>
        </div>
      )}
    />
  );
};

export default DatasetList;
