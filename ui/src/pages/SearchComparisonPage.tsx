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
// searches over the same dataset with the same input text can be combined —
// the picker enforces that once the first search is selected.
const SearchComparisonPage = () => {
  const [summaries, setSummaries] = useState<SearchSummary[]>([]);
  const [summariesLoading, setSummariesLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  // Cache of loaded search details keyed by id; selection changes only fetch
  // ids not seen before.
  const [details, setDetails] = useState<Record<string, SearchDetail>>({});
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [view, setView] = useState<ComparisonView>("chunks");
  const [error, setError] = useState<string | null>(null);

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

  return (
    <section>
      {error && (
        <p className="mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3 shadow-sm">
          {error}
        </p>
      )}

      <div className="mb-6">
        <Card title="Select searches">
          {summariesLoading ? (
            <p className="text-sm text-emd-placeholder">Loading searches…</p>
          ) : (
            <SearchPicker
              searches={summaries}
              selectedIds={selectedIds}
              onChange={setSelectedIds}
            />
          )}
        </Card>
      </div>

      {selectedIds.length > 0 && (
        <Card
          title={
            anchor
              ? `Combined results — “${anchor.inputText}” on ${anchor.datasetName || "unknown dataset"}`
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
