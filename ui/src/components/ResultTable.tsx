import React, { useState } from "react";
import ScoreRangeSelector, { metricConfig } from "./ScoreRangeSelector";
import { useFormContext } from "./FormContext";
import { options, Similarity } from "./consts";
import { Match } from "./types";
import { inputIdGroupSeparator } from "./Submit";
import DbResultTable from "./DbResultTable";

type SortKey = keyof Match | Similarity;
type SortDirection = "asc" | "desc";

const ResultTable: React.FC = () => {
  const [sortKey, setSortKey] = useState<SortKey>("model");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [useColoring, setColororingUse] = useState(false);
  const [showInputIndex, setShowInputIndex] = useState(false);
  const { state } = useFormContext();
  const { matches } = state;
  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const getMatchSourceInputIndex = (
    match: Match,
    key: "sourceInputs" | "candidateInputs"
  ): string => {
    const id = key === "sourceInputs" ? match.source_id : match.candidate_id;
    const [inputId, groupId] = id.split(inputIdGroupSeparator);
    const inputIndex = state[key].findIndex((input) => {
      return input.id === inputId;
    });
    let groupIndex = -1;
    if (groupId) {
      const groupKey =
        key === "sourceInputs"
          ? "sourceVariableGroups"
          : "candidateVariableGroups";

      groupIndex = state[groupKey].findIndex((group) => {
        return group.id === groupId;
      });
    }
    if (groupIndex === -1) {
      return `Input ${inputIndex}`;
    }
    return `Input ${inputIndex} group ${groupIndex}`;
  };

  const sortedMatches = [...matches].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];

    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
    } else {
      return sortDirection === "asc"
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    }
  });

  const [lower, setLower] = useState({
    [Similarity.COSINE]: 0.5,
    [Similarity.DOT]: 50,
    [Similarity.EUCLIDEAN]: 10,
    [Similarity.MANHATTAN]: 150,
  });

  const [higher, setHigher] = useState({
    [Similarity.COSINE]: 0.7,
    [Similarity.DOT]: 150,
    [Similarity.EUCLIDEAN]: 20,
    [Similarity.MANHATTAN]: 400,
  });

  const red = "bg-red-200";
  const green = "bg-green-200";
  const yellow = "bg-yellow-200";

  const getRowBgColor = (similarity: Similarity, score: number) => {
    if (!useColoring) return "";
    const useGreenForHigherScore = metricConfig[similarity];

    if (score < lower[similarity] && useGreenForHigherScore) return red;
    if (score < lower[similarity] && !useGreenForHigherScore) return green;

    if (score > higher[similarity] && useGreenForHigherScore) return green;
    if (score > higher[similarity] && !useGreenForHigherScore) return red;

    return yellow;
  };

  const renderHeader = (label: string, key: SortKey) => {
    let arrow = "⇅";
    if (sortKey === key) {
      arrow = sortDirection === "asc" ? "↑" : "↓";
    }
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
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.3rem",
          }}
        >
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

  // DB source mode renders Qdrant hits + their Postgres batch info instead of
  // pairwise similarity scores. Branch after all hooks to keep hook order stable.
  if (state.sourceType === "db") {
    return <DbResultTable />;
  }

  return (
    <div>
      <div className="flex justify-center">
        <div className="mb-6 border border-emd-border rounded-md bg-emd-panel shadow-sm inline-block ml-auto">
          <div className="flex flex-row">
            <label className="flex p-4 items-center justify-end gap-2 text-lg flex text-emd-text cursor-pointer">
              <input
                type="checkbox"
                checked={showInputIndex}
                onChange={() => setShowInputIndex(!showInputIndex)}
                className="accent-emd-primary w-4 h-4 "
              />
              <span>Show input numbers</span>
            </label>
            <label className="flex p-4 items-center justify-end gap-2 text-lg flex text-emd-text cursor-pointer">
              <input
                type="checkbox"
                checked={useColoring}
                onChange={() => setColororingUse(!useColoring)}
                className="accent-emd-primary w-4 h-4 "
              />
              <span>Show threshold coloring</span>
            </label>
          </div>
          {useColoring && (
            <div className="flex flex-row items-center justify-between mt-3 p-2">
              <ScoreRangeSelector
                lower={lower}
                higher={higher}
                onChange={(
                  similarity: Similarity,
                  newLower: number,
                  newHigher: number
                ) => {
                  setLower({
                    ...lower,
                    [similarity]: newLower,
                  });
                  setHigher({
                    ...higher,
                    [similarity]: newHigher,
                  });
                }}
              />
            </div>
          )}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse min-w-[800px]">
          <thead>
            <tr>
              {renderHeader("Source Text", "sourceText")}
              {renderHeader("Candidate Text", "candidateText")}
              {renderHeader("Model", "model")}
              {state.similarities.map((similarity: Similarity) =>
                renderHeader(
                  options.find((o) => o.id === similarity)?.label,
                  similarity
                )
              )}
            </tr>
          </thead>
          <tbody>
            {!sortedMatches.length ? (
              <tr>
                <td
                  colSpan={3 + state.similarities.length}
                  style={{
                    textAlign: "center",
                    padding: "0.5rem",
                    border: "1px solid #d1d5db",
                  }}
                >
                  No data
                </td>
              </tr>
            ) : (
              sortedMatches.map((match) => (
                <tr key={match.source_id + match.candidate_id + match.model}>
                  <td
                    style={{ border: "1px solid #d1d5db", padding: "0.5rem" }}
                  >
                    {showInputIndex
                      ? getMatchSourceInputIndex(match, "sourceInputs")
                      : match.sourceText}
                  </td>
                  <td
                    style={{ border: "1px solid #d1d5db", padding: "0.5rem" }}
                  >
                    {showInputIndex
                      ? getMatchSourceInputIndex(match, "candidateInputs")
                      : match.candidateText}
                  </td>
                  <td
                    style={{ border: "1px solid #d1d5db", padding: "0.5rem" }}
                  >
                    {match.model}
                  </td>
                  {state.similarities.map((similarity) => {
                    const score = match[similarity];
                    if (score) {
                      return (
                        <td
                          style={{
                            border: "1px solid #d1d5db",
                            padding: "0.5rem",
                          }}
                          key={
                            match.candidate_id +
                            match.source_id +
                            similarity +
                            match.model
                          }
                          className={getRowBgColor(similarity, score)}
                        >
                          {score.toFixed(4)}
                        </td>
                      );
                    }
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ResultTable;
