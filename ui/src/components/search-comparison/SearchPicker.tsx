import { SearchSummary } from "../../api/searches";
import { SEARCH_COLORS } from "./colors";

interface SearchPickerProps {
  searches: SearchSummary[];
  // Selection order matters: index in this array drives each search's color.
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  // When true, searches only need to share a dataset to be comparable; the
  // input text may differ between them.
  allowDifferentInputs: boolean;
}

// Format an ISO datetime string for display; returns "—" for null/undefined.
function formatDateTime(dt: string | null | undefined): string {
  if (!dt) return "—";
  return new Date(dt).toLocaleString();
}

// Checkbox list of saved searches. Results are only comparable between
// searches over the same dataset — and, unless different inputs are allowed,
// with the same input text — so once one search is selected every
// incompatible entry is disabled until the selection is cleared.
const SearchPicker: React.FC<SearchPickerProps> = ({
  searches,
  selectedIds,
  onChange,
  allowDifferentInputs,
}) => {
  const anchor = searches.find((s) => s.id === selectedIds[0]) ?? null;

  const isCompatible = (s: SearchSummary) =>
    anchor === null ||
    (s.datasetName === anchor.datasetName &&
      (allowDifferentInputs || s.inputText === anchor.inputText));

  const toggle = (id: string) =>
    onChange(
      selectedIds.includes(id)
        ? selectedIds.filter((v) => v !== id)
        : [...selectedIds, id],
    );

  if (searches.length === 0) {
    return (
      <p className="text-sm text-emd-placeholder">
        No saved searches yet. Run a search on the Compare page first.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-emd-border/15 text-left text-xs uppercase tracking-wide text-emd-placeholder">
            <th className="w-8 py-3 pr-2" aria-label="Select" />
            <th className="py-3 pr-4 font-semibold">Run</th>
            <th className="py-3 pr-4 font-semibold">Dataset</th>
            <th className="py-3 pr-4 font-semibold">Query</th>
            <th className="py-3 pr-4 font-semibold text-right">Top K</th>
            <th className="py-3 pr-4 font-semibold text-right">Results</th>
            <th className="py-3 pl-4 font-semibold text-right last:pr-1">
              Launched
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-emd-border/10">
          {searches.map((s) => {
            const selected = selectedIds.includes(s.id);
            const disabled = !selected && !isCompatible(s);
            const colorIdx = selectedIds.indexOf(s.id);
            return (
              <tr
                key={s.id}
                onClick={() => !disabled && toggle(s.id)}
                title={
                  disabled
                    ? "Different dataset or query — not comparable with the current selection"
                    : undefined
                }
                className={`text-emd-text transition-colors ${
                  disabled
                    ? "cursor-not-allowed opacity-40"
                    : "cursor-pointer hover:bg-emd-primary/5"
                } ${selected ? "bg-emd-primary/10" : ""}`}
              >
                <td className="py-3 pr-2">
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={disabled}
                    onChange={() => toggle(s.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="accent-emd-primary w-4 h-4 disabled:cursor-not-allowed"
                    aria-label={`Select search on ${s.runName || s.pipelineId}`}
                  />
                </td>
                <td className="py-3 pr-4 max-w-[14rem]">
                  <span className="flex items-center gap-2">
                    {selected && (
                      <span
                        aria-hidden
                        className={`h-2.5 w-2.5 shrink-0 rounded-full ${SEARCH_COLORS[colorIdx % SEARCH_COLORS.length]}`}
                      />
                    )}
                    <span
                      className="truncate font-medium"
                      title={s.runName || s.pipelineId}
                    >
                      {s.runName || s.pipelineId.slice(0, 8)}
                    </span>
                  </span>
                </td>
                <td className="py-3 pr-4 max-w-[10rem]">
                  <span className="block truncate" title={s.datasetName}>
                    {s.datasetName || "—"}
                  </span>
                </td>
                <td className="py-3 pr-4 max-w-xs">
                  <span className="block truncate" title={s.inputText}>
                    {s.inputText || "—"}
                  </span>
                </td>
                <td className="py-3 pr-4 text-right tabular-nums">
                  {s.topK ?? "—"}
                </td>
                <td className="py-3 pr-4 text-right tabular-nums">
                  {s.resultCount}
                </td>
                <td className="py-3 pl-4 last:pr-1 text-right whitespace-nowrap text-xs text-emd-text/70">
                  {formatDateTime(s.createdAt)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default SearchPicker;
