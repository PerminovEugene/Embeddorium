import { useEffect, useState } from "react";
import {
  fetchPipelineRun,
  fetchPipelineRunSummaries,
  fetchPipelineRunTargets,
  PipelineRunSummary,
  PipelineRunTargetsPage,
} from "../api/pipelineRuns";
import Card from "../components/common/Card";
import Select, { SelectOption } from "../components/common/Select";
import StatusBadge from "../components/ingestion-pipelines/StatusBadge";
import { PipelineStatus } from "../components/ingestion-pipelines/types";

// Number of target rows per page.
const PAGE_SIZE = 50;

// How often to re-fetch a running pipeline's data.
const POLL_INTERVAL_MS = 10_000;

// Format an ISO datetime string for display; returns "—" for null/undefined.
function formatDateTime(dt: string | null | undefined): string {
  if (!dt) return "—";
  return new Date(dt).toLocaleString();
}

// Total working time between two ISO datetimes (finished − launched), rendered
// as a compact "1h 2m 3s" string. Returns "—" if either bound is missing or the
// span is negative/invalid (e.g. a run that hasn't finished yet).
function formatDuration(
  start: string | null | undefined,
  end: string | null | undefined,
): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "—";
  const totalSeconds = Math.floor(ms / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const parts: string[] = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  parts.push(`${s}s`);
  return parts.join(" ");
}

// Color-coded status pill for crawl-target statuses (a richer set than the
// four pipeline lifecycle states; handled separately from StatusBadge, but
// styled to match it — a dot plus a soft, legible pill on the light panel).
function TargetStatusBadge({ status }: { status: string }) {
  let pill: string;
  let dot: string;
  if (status === "processed") {
    pill = "bg-green-50 text-green-700 border-green-200";
    dot = "bg-green-500";
  } else if (status.startsWith("failed")) {
    pill = "bg-red-50 text-red-700 border-red-200";
    dot = "bg-red-500";
  } else if (status.startsWith("skipped")) {
    pill = "bg-amber-50 text-amber-700 border-amber-200";
    dot = "bg-amber-500";
  } else {
    pill = "bg-slate-100 text-slate-600 border-slate-300";
    dot = "bg-slate-400";
  }
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide ${pill}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} aria-hidden="true" />
      {status.replace(/_/g, " ")}
    </span>
  );
}

const PipelineRunsPage = () => {
  const [runs, setRuns] = useState<PipelineRunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [runInfo, setRunInfo] = useState<PipelineRunSummary | null>(null);
  const [targetsPage, setTargetsPage] = useState<PipelineRunTargetsPage | null>(
    null,
  );
  const [offset, setOffset] = useState(0);
  const [runsLoading, setRunsLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Bumped each time a poll cycle starts; used as a React key to restart the
  // countdown-bar CSS animation so the fill always tracks the next poll.
  const [pollCycle, setPollCycle] = useState(0);

  // Load the runs list on mount; auto-select the newest (index 0 = newest
  // because the endpoint returns newest-first).
  useEffect(() => {
    let active = true;
    setRunsLoading(true);
    fetchPipelineRunSummaries()
      .then((data) => {
        if (!active) return;
        setRuns(data);
        if (data.length > 0) {
          setSelectedId(data[0].id);
        }
      })
      .catch((err) => {
        console.error("Failed to load pipeline runs:", err);
        if (active) setError("Failed to load pipeline runs");
      })
      .finally(() => {
        if (active) setRunsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // Fetch the selected run's info + current page of targets whenever the
  // selection or page offset changes.
  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([
      fetchPipelineRun(selectedId),
      fetchPipelineRunTargets(selectedId, { limit: PAGE_SIZE, offset }),
    ])
      .then(([info, page]) => {
        if (!active) return;
        setRunInfo(info);
        setTargetsPage(page);
      })
      .catch((err) => {
        console.error("Failed to load run details:", err);
        if (active)
          setError(
            err instanceof Error ? err.message : "Failed to load run details",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId, offset]);

  // Poll every 10 s while the selected run's status is "running". The effect
  // re-runs (clearing the previous interval) whenever status or offset changes,
  // so it always polls the current page and stops automatically once the run
  // leaves the "running" state. A `cancelled` flag guards against setState
  // calls from in-flight fetches after the interval is cleared.
  useEffect(() => {
    if (!selectedId || !runInfo || runInfo.status !== "running") return;
    let cancelled = false;
    // Restart the countdown bar whenever a new poll window opens (both when
    // polling begins and after each interval tick below).
    setPollCycle((c) => c + 1);
    const id = setInterval(() => {
      setPollCycle((c) => c + 1);
      Promise.all([
        fetchPipelineRun(selectedId),
        fetchPipelineRunTargets(selectedId, { limit: PAGE_SIZE, offset }),
      ])
        .then(([info, page]) => {
          if (cancelled) return;
          setRunInfo(info);
          setTargetsPage(page);
        })
        .catch(() => {
          // Swallow poll errors — a transient network blip shouldn't interrupt
          // the display of the last-known state.
        });
    }, 10_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selectedId, runInfo?.status, offset]);

  // Reset to page 0 and clear stale data when the user switches runs.
  const handleSelectRun = (id: string) => {
    if (id === selectedId) return;
    setSelectedId(id);
    setOffset(0);
    setRunInfo(null);
    setTargetsPage(null);
  };

  // Enrich each option with status + created date so runs are distinguishable
  // in the dropdown (names alone are often identical across re-runs).
  const runOptions: SelectOption[] = runs.map((r) => ({
    value: r.id,
    label: [
      r.name ?? r.id,
      r.status,
      r.createdAt ? formatDateTime(r.createdAt) : null,
    ]
      .filter(Boolean)
      .join("  ·  "),
  }));

  const total = targetsPage?.total ?? 0;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + PAGE_SIZE, total);

  // The countdown bar is shown only while we're actively polling a running run.
  const isPolling = Boolean(selectedId) && runInfo?.status === "running";

  return (
    <section>
      {/* Poll-countdown bar: fills over one poll interval, restarting on each
          poll (keyed by pollCycle), so the user can see when the next data
          refresh will happen. Hidden when the pipeline isn't in progress. */}
      {isPolling && (
        <div
          className="mb-6 h-1.5 overflow-hidden rounded-full bg-white/10"
          role="progressbar"
          aria-label="Time until next data refresh"
          title="Live run — the bar shows when the data refreshes next"
        >
          <div
            key={pollCycle}
            className="h-full rounded-full bg-emd-primary"
            style={{
              animation: `emd-poll-progress ${POLL_INTERVAL_MS}ms linear forwards`,
            }}
          />
        </div>
      )}

      {error && (
        <p className="mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3 shadow-sm">
          {error}
        </p>
      )}

      {/* Run selector */}
      <div className="mb-6">
        <Card title="Select run">
          {runsLoading ? (
            <p className="text-sm text-emd-placeholder">Loading runs…</p>
          ) : runs.length === 0 ? (
            <p className="text-sm text-emd-placeholder">No pipeline runs found.</p>
          ) : (
            <Select
              options={runOptions}
              value={selectedId ?? ""}
              onChange={(e) => handleSelectRun(e.target.value)}
            />
          )}
        </Card>
      </div>

      {/* Initial loading state before the first fetch resolves */}
      {selectedId && loading && !runInfo && (
        <p className="mb-6 text-sm text-emd-placeholder">Loading run details…</p>
      )}

      {/* Run info card — shown as soon as we have run data */}
      {selectedId && runInfo && (
        <div className="mb-6">
          <Card title="Run details">
            <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-3">
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.15em] text-emd-placeholder">
                  Name
                </dt>
                <dd className="mt-0.5 text-sm text-emd-text">
                  {runInfo.name ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.15em] text-emd-placeholder">
                  Status
                </dt>
                <dd className="mt-0.5">
                  <StatusBadge status={runInfo.status as PipelineStatus} />
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.15em] text-emd-placeholder">
                  Launched
                </dt>
                <dd className="mt-0.5 text-sm text-emd-text">
                  {formatDateTime(runInfo.startedAt)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.15em] text-emd-placeholder">
                  Finished
                </dt>
                <dd className="mt-0.5 text-sm text-emd-text">
                  {formatDateTime(runInfo.finishedAt)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.15em] text-emd-placeholder">
                  Working time
                </dt>
                <dd className="mt-0.5 text-sm text-emd-text">
                  {formatDuration(runInfo.startedAt, runInfo.finishedAt)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold uppercase tracking-[0.15em] text-emd-placeholder">
                  Chunks
                </dt>
                <dd className="mt-0.5 text-sm text-emd-text tabular-nums">
                  {runInfo.chunksEmbedded} chunks processed / {runInfo.chunksPending}{" "}
                  chunks in progress
                </dd>
              </div>
            </dl>
          </Card>
        </div>
      )}

      {/* Targets table — rendered once a run is selected (uses loading/empty
          states internally to avoid a layout shift on the first load) */}
      {selectedId && (runInfo || loading) && (
        <Card
          title={
            total > 0
              ? `Processed files / URLs (${total})`
              : "Processed files / URLs"
          }
        >
          {loading && !targetsPage ? (
            <p className="text-sm text-emd-placeholder">Loading…</p>
          ) : !targetsPage || targetsPage.items.length === 0 ? (
            <p className="text-sm text-emd-placeholder">No targets yet.</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-emd-border/15 text-left text-xs uppercase tracking-wide text-emd-placeholder">
                      <th className="py-3 pr-4 font-semibold first:pl-1">
                        File / URL
                      </th>
                      <th className="py-3 pr-4 font-semibold">Status</th>
                      <th className="py-3 pr-4 font-semibold">Detail</th>
                      <th className="py-3 pr-4 font-semibold text-right">Chunks</th>
                      <th className="py-3 pl-4 font-semibold text-right last:pr-1">
                        Processing time
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-emd-border/10">
                    {targetsPage.items.map((t) => (
                      <tr
                        key={t.id}
                        className="text-emd-text transition-colors hover:bg-emd-primary/5"
                      >
                        <td className="py-3 pr-4 first:pl-1 max-w-xs align-top">
                          {/* Primary URL */}
                          <span
                            className="block truncate font-mono text-xs"
                            title={t.url}
                          >
                            {t.url}
                          </span>
                          {/* Normalised form shown only when it differs */}
                          {t.normalizedUrl && t.normalizedUrl !== t.url && (
                            <span
                              className="mt-0.5 block truncate font-mono text-xs text-emd-placeholder"
                              title={t.normalizedUrl}
                            >
                              {t.normalizedUrl}
                            </span>
                          )}
                        </td>
                        <td className="py-3 pr-4 whitespace-nowrap align-top">
                          <TargetStatusBadge status={t.status} />
                        </td>
                        <td className="py-3 pr-4 max-w-xs align-top">
                          <span
                            className="block truncate text-xs text-emd-text/70"
                            title={t.skipReason ?? t.error ?? ""}
                          >
                            {t.skipReason ?? t.error ?? "—"}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-right align-top tabular-nums">
                          {t.chunkCount}
                        </td>
                        <td className="py-3 pl-4 last:pr-1 text-right align-top tabular-nums">
                          {formatDuration(t.createdAt, t.processedAt)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination controls */}
              <div className="mt-5 flex items-center justify-between gap-4">
                <span className="text-xs text-emd-placeholder">
                  {total === 0
                    ? "No results"
                    : `Showing ${rangeStart}–${rangeEnd} of ${total}`}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={offset === 0}
                    onClick={() =>
                      setOffset((prev) => Math.max(0, prev - PAGE_SIZE))
                    }
                    className="px-3 py-1 rounded-md border border-emd-border text-xs font-semibold transition hover:bg-emd-accent/10 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Prev
                  </button>
                  <button
                    type="button"
                    disabled={offset + PAGE_SIZE >= total}
                    onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                    className="px-3 py-1 rounded-md border border-emd-border text-xs font-semibold transition hover:bg-emd-accent/10 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </Card>
      )}
    </section>
  );
};

export default PipelineRunsPage;
