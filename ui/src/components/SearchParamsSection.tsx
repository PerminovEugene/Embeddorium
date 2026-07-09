import React from "react";
import { useFormContext } from "./FormContext";
import { inputStyle } from "../styles/styles";
import { SearchMethod } from "./types";
import TopKInput from "./TopKInput";
import Checkbox from "./common/Checkbox";

const methods: { id: SearchMethod; label: string }[] = [
  { id: "embedding", label: "Embedding (vector)" },
  { id: "bm25", label: "BM25 (lexical)" },
];

// DB-search mode only: parameters of the search itself — how queries are
// matched, how many results to return, and whether the launch is saved to the
// search history.
const SearchParamsSection: React.FC = () => {
  const { state, setSearchMethod, setSaveResults } = useFormContext();

  return (
    <div className="flex flex-row flex-wrap items-start gap-8">
      <div className="flex flex-col" style={{ minWidth: 220 }}>
        <label
          className="text-sm font-medium text-emd-text mb-1"
          htmlFor="search-method"
        >
          Search type
        </label>
        <select
          id="search-method"
          style={inputStyle}
          value={state.searchMethod}
          onChange={(e) => setSearchMethod(e.target.value as SearchMethod)}
        >
          {methods.map(({ id, label }) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <span className="text-xs text-emd-text mt-1">
          How queries are matched against the collection
        </span>
      </div>

      <TopKInput />

      <div className="flex flex-col">
        <span className="text-sm font-medium text-emd-text mb-1">History</span>
        <div className="py-2">
          <Checkbox
            label="Save search results"
            checked={state.saveResults}
            onChange={(e) => setSaveResults(e.target.checked)}
          />
        </div>
        <span className="text-xs text-emd-text">
          Saved searches appear on the comparison page
        </span>
      </div>
    </div>
  );
};

export default SearchParamsSection;
