import React from "react";
import { PipelineStatus } from "./types";

// Color-coded pill for a pipeline's lifecycle status. Each entry carries the
// pill palette plus a matching status dot; `running` pulses to signal that the
// page is actively polling.
const STYLES: Record<PipelineStatus, { pill: string; dot: string }> = {
  pending: { pill: "bg-slate-100 text-slate-600 border-slate-300", dot: "bg-slate-400" },
  running: { pill: "bg-blue-50 text-blue-700 border-blue-200", dot: "bg-blue-500 animate-pulse" },
  completed: { pill: "bg-green-50 text-green-700 border-green-200", dot: "bg-green-500" },
  failed: { pill: "bg-red-50 text-red-700 border-red-200", dot: "bg-red-500" },
};

const StatusBadge: React.FC<{ status: PipelineStatus }> = ({ status }) => {
  const { pill, dot } = STYLES[status];
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${pill}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} aria-hidden="true" />
      {status}
    </span>
  );
};

export default StatusBadge;
