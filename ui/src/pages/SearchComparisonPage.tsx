import { useEffect, useMemo, useState } from "react";
import {
  fetchSearch,
  fetchSearchSummaries,
  SearchDetail,
  SearchSummary,
} from "../api/searches";
import Card from "../components/common/Card";
import ComparisonTable from "../components/search-comparison/ComparisonTable";
import SearchPicker from "../components/search-comparison/SearchPicker";
import { ComparisonView, flattenHits } from "../components/search-comparison/combine";

const VIEWS: { value: ComparisonView; label: string }[] = [
  { value: "chunks", label: "By chunk" },
  { value: "documents", label: "By document" },
  { value: "ranks", label: "By rank" },
];

// Compare the stored results of several saved searches side by side. Only
// searches over the same dataset can be combined; by default they must also
// share the same input text, unless "Allow different inputs" is enabled. The
// picker enforces the active rule once the first search is selected.
const SearchComparisonPage = () => {
  const [summaries, setSummaries] = useState<SearchSummary[]>([]);
  const [summariesLoading, setSummariesLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [allowDifferentInputs, setAllowDifferentInputs] = useState(false);
  // Cache of loaded search details keyed by id; selection changes only fetch
  // ids not seen before.
  const [details, setDetails] = useState<Record<string, SearchDetail>>({});
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [view, setView] = useState<ComparisonView>("chunks");
  const [error, setError] = useState<string | null>(null);

  // Turning the option off can leave searches with mismatching queries in the
  // selection; drop everything that no longer matches the anchor's query.
  const handleAllowDifferentInputsChange = (allow: boolean) => {
    setAllowDifferentInputs(allow);
    if (allow || selectedIds.length < 2) return;
    const anchor = summaries.find((s) => s.id === selectedIds[0]);
    if (!anchor) return;
    setSelectedIds(
      selectedIds.filter(
        (id) =>
          summaries.find((s) => s.id === id)?.inputText === anchor.inputText,
      ),
    );
  };

  useEffect(() => {
    let active = true;
    fetchSearchSummaries()
      .then((data) => {
        if (active) setSummaries(data);
      })
      .catch((err) => {
        console.error("Failed to load saved searches:", err);
        if (active) setError("Failed to load saved searches");
      })
      .finally(() => {
        if (active) setSummariesLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // Fetch stored results for newly selected searches.
  useEffect(() => {
    const missing = selectedIds.filter((id) => !(id in details));
    if (missing.length === 0) return;
    let active = true;
    setDetailsLoading(true);
    setError(null);
    Promise.all(missing.map(fetchSearch))
      .then((loaded) => {
        if (!active) return;
        setDetails((prev) => {
          const next = { ...prev };
          for (const d of loaded) next[d.id] = d;
          return next;
        });
      })
      .catch((err) => {
        console.error("Failed to load search results:", err);
        if (active)
          setError(
            err instanceof Error ? err.message : "Failed to load search results",
          );
      })
      .finally(() => {
        if (active) setDetailsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedIds, details]);

  // Details in selection order — the index doubles as each search's color, so
  // it must match the picker's selection-order color assignment.
  const selectedDetails = useMemo(
    () =>
      selectedIds
        .map((id) => details[id])
        .filter((d): d is SearchDetail => d !== undefined),
    [selectedIds, details],
  );

  const hits = useMemo(() => flattenHits(selectedDetails), [selectedDetails]);
  const anchor = selectedDetails[0] ?? null;
  const distinctQueries = new Set(selectedDetails.map((d) => d.inputText)).size;

  return (
    <section>
      {error && (
        <p className="mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3 shadow-sm">
          {error}
        </p>
      )}

      <div className="mb-6">
        {summariesLoading ? (
          <Card title="Select searches">
            <p className="text-sm text-emd-placeholder">Loading searches…</p>
          </Card>
        ) : summaries.length === 0 ? (
          <Card title="No saved searches yet">
            <p className="text-sm text-emd-placeholder">
              There are no saved searches to compare. Run a search first, then
              come back here to compare the stored results side by side.
            </p>
          </Card>
        ) : (
          <Card title="Select searches">
              <label className="mb-3 flex w-fit cursor-pointer items-center gap-2 text-sm text-emd-text">
                <input
                  type="checkbox"
                  checked={allowDifferentInputs}
                  onChange={(e) =>
                    handleAllowDifferentInputsChange(e.target.checked)
                  }
                  className="accent-emd-primary w-4 h-4"
                />
                <span>Allow different inputs</span>
                <span className="text-xs text-emd-placeholder">
                  — compare searches with different queries on the same dataset
                </span>
              </label>
              <SearchPicker
                searches={summaries}
                selectedIds={selectedIds}
                onChange={setSelectedIds}
                allowDifferentInputs={allowDifferentInputs}
              />
          </Card>
        )}
      </div>

      {selectedIds.length > 0 && (
        <Card
          title={
            anchor
              ? distinctQueries > 1
                ? `Combined results — ${distinctQueries} queries on ${anchor.datasetName || "unknown dataset"}`
                : `Combined results — “${anchor.inputText}” on ${anchor.datasetName || "unknown dataset"}`
              : "Combined results"
          }
        >
          {/* View switcher */}
          <div className="mb-4 inline-flex rounded-lg border border-emd-border p-0.5">
            {VIEWS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setView(value)}
                className={`px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wide transition ${
                  view === value
                    ? "bg-emd-primary text-white"
                    : "text-emd-text/70 hover:bg-emd-accent/10"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {detailsLoading && selectedDetails.length < selectedIds.length ? (
            <p className="text-sm text-emd-placeholder">Loading results…</p>
          ) : (
            <ComparisonTable hits={hits} view={view} />
          )}
        </Card>
      )}
    </section>
  );
};

export default SearchComparisonPage;
