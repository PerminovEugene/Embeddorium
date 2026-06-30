import React from "react";
import { PipelineStatus } from "./types";

// Color-coded pill for a pipeline's lifecycle status.
const STYLES: Record<PipelineStatus, string> = {
  pending: "bg-gray-100 text-gray-700 border-gray-300",
  running: "bg-blue-100 text-blue-700 border-blue-300",
  completed: "bg-green-100 text-green-700 border-green-300",
  failed: "bg-red-100 text-red-700 border-red-300",
};

const StatusBadge: React.FC<{ status: PipelineStatus }> = ({ status }) => (
  <span
    className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${STYLES[status]}`}
  >
    {status}
  </span>
);

export default StatusBadge;
