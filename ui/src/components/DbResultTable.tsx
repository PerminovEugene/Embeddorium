import React, { useState } from "react";
import { useFormContext } from "./FormContext";
import { DbMatch } from "./types";

type SortKey = keyof DbMatch;
type SortDirection = "asc" | "desc";

const columns: { key: SortKey; label: string }[] = [
  { key: "queryText", label: "Query" },
  { key: "chunkText", label: "Chunk Text" },
  { key: "score", label: "Score" },
  { key: "sourceUrl", label: "Source URL" },
  { key: "group", label: "Group" },
  { key: "chunkIndex", label: "Chunk #" },
  { key: "documentId", label: "Document ID" },
];

const cellStyle = { border: "1px solid #d1d5db", padding: "0.5rem" } as const;

const DbResultTable: React.FC = () => {
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const { state } = useFormContext();
  const { dbMatches = [] } = state;

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
  };

  const sortedMatches = [...dbMatches].sort((a, b) => {
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

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse min-w-[800px]">
        <thead>
          <tr>{columns.map((c) => renderHeader(c.label, c.key))}</tr>
        </thead>
        <tbody>
          {!sortedMatches.length ? (
            <tr>
              <td colSpan={columns.length} style={{ ...cellStyle, textAlign: "center" }}>
                No data
              </td>
            </tr>
          ) : (
            sortedMatches.map((match, index) => (
              <tr key={`${match.source_id}-${match.chunkId}-${index}`}>
                <td style={cellStyle}>{match.queryText}</td>
                <td style={cellStyle}>{match.chunkText ?? "—"}</td>
                <td style={cellStyle}>
                  {typeof match.score === "number" ? match.score.toFixed(4) : "—"}
                </td>
                <td style={cellStyle}>
                  {match.sourceUrl ? (
                    <a
                      href={match.sourceUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="text-emd-primary underline"
                    >
                      {match.sourceUrl}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                <td style={cellStyle}>{match.group ?? "—"}</td>
                <td style={cellStyle}>{match.chunkIndex ?? "—"}</td>
                <td style={cellStyle}>{match.documentId ?? "—"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default DbResultTable;
