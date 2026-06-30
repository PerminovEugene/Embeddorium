import React from "react";
import { IngestionPipeline } from "./types";
import StatusBadge from "./StatusBadge";

interface IngestionPipelineListProps {
  pipelines: IngestionPipeline[];
  // Currently selected pipeline (shown read-only in the form), or null.
  selectedId: string | null;
  // Open a pipeline for read-only viewing.
  onSelect: (pipeline: IngestionPipeline) => void;
  // Launch (or relaunch) a pipeline's run.
  onLaunch: (pipeline: IngestionPipeline) => void;
  onDelete: (pipeline: IngestionPipeline) => void;
  // Id of the pipeline whose launch/delete request is in flight, if any.
  busyId: string | null;
  loading?: boolean;
}

// List of pipelines with per-row status and Launch/Relaunch + Delete actions.
// Rows are selectable to open the pipeline read-only in the form.
const IngestionPipelineList: React.FC<IngestionPipelineListProps> = ({
  pipelines,
  selectedId,
  onSelect,
  onLaunch,
  onDelete,
  busyId,
  loading,
}) => {
  if (loading) {
    return <p className="text-emd-placeholder text-sm p-3">Loading…</p>;
  }
  if (pipelines.length === 0) {
    return <p className="text-emd-placeholder text-sm p-3">No pipelines yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-2 max-h-[60vh] overflow-auto">
      {pipelines.map((p) => {
        const busy = busyId === p.id;
        // "running" can't be launched again; pending launches, terminal relaunches.
        const canLaunch = p.status !== "running";
        const launchLabel = p.status === "pending" ? "Launch" : "Relaunch";
        const subtitle = [p.collection, p.embedModel].filter(Boolean).join(" · ");
        const selected = selectedId === p.id;

        return (
          <li
            key={p.id}
            onClick={() => onSelect(p)}
            className={`rounded-md border bg-white px-3 py-2.5 flex flex-col gap-2 cursor-pointer transition-colors ${
              selected
                ? "border-emd-primary ring-2 ring-emd-primary/40"
                : "border-emd-border hover:border-emd-primary/50"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium truncate">{p.name}</span>
              <StatusBadge status={p.status} />
            </div>
            {subtitle && (
              <span className="text-xs opacity-70 truncate">{subtitle}</span>
            )}
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={busy || !canLaunch}
                onClick={(e) => {
                  e.stopPropagation();
                  onLaunch(p);
                }}
                className="px-3 py-1.5 rounded-md bg-emd-accent text-emd-button-text text-sm font-semibold hover:bg-emd-primary transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy ? "…" : launchLabel}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(p);
                }}
                className="px-3 py-1.5 rounded-md border border-red-500 text-red-600 text-sm font-semibold hover:bg-red-500 hover:text-white transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Delete
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
};

export default IngestionPipelineList;
