import React, { useState } from "react";
import { useFormContext } from "./FormContext";
import { DbMatch } from "./types";

type SortKey = keyof DbMatch;
type SortDirection = "asc" | "desc";

// Leading sortable columns. The chunk metadata (source / group / chunk # /
// document id) is collapsed into one non-sortable cell, and Score is rendered
// as the trailing column — both handled separately below.
const columns: { key: SortKey; label: string }[] = [
  { key: "queryText", label: "Query" },
  { key: "chunkText", label: "Chunk Text" },
];

const cellStyle = { border: "1px solid #d1d5db", padding: "0.5rem" } as const;

// For a local dataset source_url is an absolute filesystem path; show just the
// file name (full path stays available as a tooltip).
const fileName = (path: string): string => path.split(/[\\/]/).pop() || path;

const DbResultTable: React.FC = () => {
  // Default to the order the backend returned (best-first rank order). Score
  // semantics vary by strategy — keyword (BM25) scores are negated so lower is
  // better, while semantic/hybrid scores are higher-is-better — so we must not
  // re-sort by raw score. Users can still opt into a column sort by clicking a
  // header (null = keep received order).
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const { state } = useFormContext();
  const { dbMatches = [], selectedRun } = state;

  // Web runs expose a real URL (rendered as a link); local runs expose a file
  // path (rendered as a file name). Both surface inside the chunk metadata cell.
  const isLocal = selectedRun?.sourceType === "local";
  const sourceLabel = isLocal ? "File" : "Source";

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
  };

  const sortedMatches =
    sortKey === null
      ? dbMatches
      : [...dbMatches].sort((a, b) => {
          const aVal = a[sortKey];
          const bVal = b[sortKey];
          if (typeof aVal === "number" && typeof bVal === "number") {
            return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
          }
          return sortDirection === "asc"
            ? String(aVal).localeCompare(String(bVal))
            : String(bVal).localeCompare(String(aVal));
        });

  const renderHeader = (label: string, key: SortKey) => {
    let arrow = "⇅";
    if (sortKey === key) arrow = sortDirection === "asc" ? "↑" : "↓";
    return (
      <th
        onClick={() => handleSort(key)}
        key={key}
        style={{
          border: "1px solid #d1d5db",
          padding: "0.5rem",
          textAlign: "left",
          cursor: "pointer",
          userSelect: "none",
          backgroundColor: sortKey === key ? "#e5e7eb" : "transparent",
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
          {label}
          <span
            style={{
              fontSize: "1rem",
              fontWeight: sortKey === key ? "bold" : "normal",
              color: sortKey === key ? "green" : "grey",
            }}
          >
            {arrow}
          </span>
        </span>
      </th>
    );
  };

  const colCount = columns.length + 2; // + chunk metadata + score columns

  const renderSource = (match: DbMatch) => {
    if (!match.sourceUrl) return "—";
    if (isLocal) {
      return (
        <span
          title={match.sourceUrl}
          className="inline-flex items-center gap-1 max-w-[220px] align-bottom"
        >
          <span aria-hidden>📄</span>
          <span className="truncate">{fileName(match.sourceUrl)}</span>
        </span>
      );
    }
    return (
      <a
        href={match.sourceUrl}
        target="_blank"
        rel="noreferrer"
        className="text-emd-primary underline break-all"
      >
        {match.sourceUrl}
      </a>
    );
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse min-w-[800px]">
        <thead>
          <tr>
            {columns.map((c) => renderHeader(c.label, c.key))}
            <th
              style={{
                border: "1px solid #d1d5db",
                padding: "0.5rem",
                textAlign: "left",
                userSelect: "none",
              }}
            >
              Chunk metadata
            </th>
            {renderHeader("Score", "score")}
          </tr>
        </thead>
        <tbody>
          {!sortedMatches.length ? (
            <tr>
              <td colSpan={colCount} style={{ ...cellStyle, textAlign: "center" }}>
                No data
              </td>
            </tr>
          ) : (
            sortedMatches.map((match, index) => (
              <tr key={`${match.source_id}-${match.chunkId}-${index}`}>
                <td style={cellStyle}>{match.queryText}</td>
                <td style={cellStyle}>{match.chunkText ?? "—"}</td>
                <td style={cellStyle}>
                  <div className="flex flex-col gap-0.5 text-xs text-emd-text">
                    <span className="inline-flex items-baseline gap-1 max-w-[240px]">
                      <span className="font-medium shrink-0">{sourceLabel}:</span>{" "}
                      {renderSource(match)}
                    </span>
                    {/* Web runs identify the origin by dataset; local runs use
                        the ingest group instead. */}
                    {isLocal ? (
                      <span>
                        <span className="font-medium">Group:</span>{" "}
                        {match.group ?? "—"}
                      </span>
                    ) : (
                      <span>
                        <span className="font-medium">Dataset:</span>{" "}
                        {selectedRun?.group ?? "—"}
                      </span>
                    )}
                    <span>
                      <span className="font-medium">Chunk #:</span>{" "}
                      {match.chunkIndex ?? "—"}
                    </span>
                    <span
                      className="truncate max-w-[220px]"
                      title={match.documentId ?? undefined}
                    >
                      <span className="font-medium">Doc:</span>{" "}
                      {match.documentId ?? "—"}
                    </span>
                  </div>
                </td>
                <td style={cellStyle}>
                  {typeof match.score === "number" ? match.score.toFixed(4) : "—"}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default DbResultTable;
