import React, { useEffect, useState } from "react";
import { useFormContext } from "./FormContext";
import { inputStyle } from "../styles/styles";
import { SERVER_URL } from "./consts";
import { PipelineRun } from "./types";

const runLabel = (run: PipelineRun): string =>
  `${run.name} · ${run.group} (${run.embedProvider}/${run.embedModel})`;

// Raw shape of GET /pipeline-runs: a bare array whose top-level keys are
// camelCase, but whose nested dataset/actorConfigs snapshots are raw model
// dumps (snake_case). The flat PipelineRun the selector renders is reconstructed
// from those snapshots here.
interface PipelineRunRaw {
  id: string;
  name?: string | null;
  dataset?: { name?: string; source_type?: string };
  actorConfigs?: {
    chunk_document?: {
      strategy?: string;
      chunk_size?: number;
      chunk_overlap?: number;
    };
    vector_store?: { collection?: string; similarity?: string };
    embed_chunks?: {
      provider?: {
        name?: string;
        provider_type?: string;
        model_name?: string;
        model?: string;
      };
    };
  };
  createdAt?: string | null;
}

const toRun = (raw: PipelineRunRaw): PipelineRun => {
  const chunk = raw.actorConfigs?.chunk_document ?? {};
  const vector = raw.actorConfigs?.vector_store ?? {};
  const provider = raw.actorConfigs?.embed_chunks?.provider ?? {};
  return {
    id: raw.id,
    name: raw.name?.trim() || raw.dataset?.name || "(unnamed pipeline)",
    group: raw.dataset?.name ?? "(unnamed dataset)",
    sourceType: raw.dataset?.source_type ?? "",
    collection: vector.collection ?? "",
    embedProvider: provider.name ?? provider.provider_type ?? "",
    embedModel: provider.model_name ?? provider.model ?? "",
    similarity: vector.similarity ?? "",
    chunkStrategy: chunk.strategy ?? "",
    chunkSize: chunk.chunk_size ?? 0,
    chunkOverlap: chunk.chunk_overlap ?? 0,
    createdAt: raw.createdAt ?? null,
  };
};

const RunSelector: React.FC = () => {
  const { state, setSelectedRun } = useFormContext();
  const { selectedRun } = state;

  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = () => {
    setLoading(true);
    setError(null);
    fetch(`${SERVER_URL}/pipeline-runs`)
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        return res.json();
      })
      .then((result) => {
        // The endpoint returns a bare array; tolerate a {runs: [...]} wrapper too.
        const raw: PipelineRunRaw[] = Array.isArray(result)
          ? result
          : result?.runs ?? [];
        const loaded: PipelineRun[] = raw.map(toRun);
        setRuns(loaded);
        // Re-sync the selected run with the freshly loaded list (its config may
        // have changed), or clear it if it no longer exists.
        if (selectedRun) {
          setSelectedRun(loaded.find((r) => r.id === selectedRun.id) ?? null);
        }
      })
      .catch((err) => {
        console.error("Failed to load pipeline runs:", err);
        setError("Failed to load pipeline runs");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const run = runs.find((r) => r.id === e.target.value) ?? null;
    setSelectedRun(run);
  };

  return (
    <div className="flex flex-col mr-5" style={{ minWidth: 320 }}>
      <label className="text-sm font-medium text-emd-text mb-1">
        Pipeline run
      </label>
      <div className="flex flex-row items-center gap-2">
        <select
          style={inputStyle}
          value={selectedRun?.id ?? ""}
          onChange={handleChange}
        >
          <option value="">
            {loading ? "Loading…" : "Select a pipeline run"}
          </option>
          {runs.map((run) => (
            <option key={run.id} value={run.id}>
              {runLabel(run)}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={loadRuns}
          title="Refresh pipeline runs"
          style={{
            padding: "0.5rem 0.75rem",
            border: "1px solid #d1d5db",
            borderRadius: "0.375rem",
            background: "white",
            cursor: "pointer",
          }}
        >
          ↻
        </button>
      </div>
      {error && <span className="text-red-500 text-sm mt-1">{error}</span>}
      {selectedRun && (
        <div className="text-xs text-emd-text mt-2 leading-5">
          <div>
            <span className="font-medium">Collection:</span>{" "}
            {selectedRun.collection}
          </div>
          <div>
            <span className="font-medium">Embed:</span>{" "}
            {selectedRun.embedProvider} / {selectedRun.embedModel}
          </div>
          <div>
            <span className="font-medium">Similarity:</span>{" "}
            {selectedRun.similarity} ·{" "}
            <span className="font-medium">Chunk:</span>{" "}
            {selectedRun.chunkStrategy === "section" ? (
              "By section"
            ) : (
              <>
                {selectedRun.chunkSize}/{selectedRun.chunkOverlap}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RunSelector;
