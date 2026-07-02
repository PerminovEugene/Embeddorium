import { useEffect, useMemo, useState } from "react";
import {
  createIngestionPipelines,
  deleteIngestionPipeline,
  fetchIngestionPipelines,
  launchIngestionPipeline,
} from "../api/ingestionPipelines";
import { fetchProviders } from "../api/providers";
import { fetchDatasets } from "../api/datasets";
import { fetchChunkers } from "../api/chunkers";
import IngestionPipelineList from "../components/ingestion-pipelines/IngestionPipelineList";
import IngestionPipelineForm from "../components/ingestion-pipelines/IngestionPipelineForm";
import {
  ChunkerConfig,
  IngestionPipeline,
  IngestionPipelineFormValues,
} from "../components/ingestion-pipelines/types";
import { Provider } from "../components/providers/types";
import { Dataset } from "../components/datasets/types";
import Card from "../components/common/Card";

const IngestionPipelinesPage = () => {
  const [pipelines, setPipelines] = useState<IngestionPipeline[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [chunkers, setChunkers] = useState<ChunkerConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  // Id of the pipeline whose launch/delete request is in flight, if any.
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // null selection === "create new"; a selected pipeline is shown read-only.
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedPipeline = useMemo(
    () => pipelines.find((p) => p.id === selectedId) ?? null,
    [pipelines, selectedId],
  );

  const handleCreateNew = () => setSelectedId(null);

  useEffect(() => {
    let active = true;
    // Pipelines own the page; providers/datasets feed the form's selectors.
    // A failure loading the latter shouldn't blank the whole page.
    Promise.all([
      fetchIngestionPipelines(),
      fetchProviders().catch((err) => {
        console.error("Failed to load providers:", err);
        return [] as Provider[];
      }),
      fetchDatasets().catch((err) => {
        console.error("Failed to load datasets:", err);
        return [] as Dataset[];
      }),
      fetchChunkers().catch((err) => {
        console.error("Failed to load chunkers:", err);
        return [] as ChunkerConfig[];
      }),
    ])
      .then(([pipelineData, providerData, datasetData, chunkerData]) => {
        if (!active) return;
        setPipelines(pipelineData);
        setProviders(providerData);
        setDatasets(datasetData);
        setChunkers(chunkerData);
      })
      .catch((err) => {
        console.error("Failed to load ingestion pipelines:", err);
        if (active) setError("Failed to load ingestion pipelines");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (values: IngestionPipelineFormValues) => {
    setSubmitting(true);
    setError(null);
    try {
      // Creating fans out into one run per selected dataset; refetch to pick up
      // the server-assigned ids/status for all of them.
      await createIngestionPipelines(values);
      setPipelines(await fetchIngestionPipelines());
    } catch (err) {
      console.error("Failed to create ingestion pipeline:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to create ingestion pipeline",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleLaunch = async (pipeline: IngestionPipeline) => {
    setBusyId(pipeline.id);
    setError(null);
    try {
      const updated = await launchIngestionPipeline(pipeline.id);
      setPipelines((prev) =>
        prev.map((p) => (p.id === updated.id ? updated : p)),
      );
    } catch (err) {
      console.error("Failed to launch pipeline:", err);
      setError(
        err instanceof Error ? err.message : "Failed to launch pipeline",
      );
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (pipeline: IngestionPipeline) => {
    if (!window.confirm(`Delete pipeline "${pipeline.name}"?`)) return;
    setBusyId(pipeline.id);
    setError(null);
    try {
      await deleteIngestionPipeline(pipeline.id);
      setPipelines((prev) => prev.filter((p) => p.id !== pipeline.id));
      // Drop the selection if we just removed the pipeline being viewed.
      setSelectedId((prev) => (prev === pipeline.id ? null : prev));
    } catch (err) {
      console.error("Failed to delete pipeline:", err);
      setError("Failed to delete pipeline");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section>
      {error && (
        <p className="mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3 shadow-sm">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-[22rem_1fr] gap-6 items-start">
        {/* Left: "create new" action above the live pipeline list with per-row
            launch/delete + status. Selecting a row opens it read-only. */}
        <aside className="flex flex-col gap-3 md:sticky md:top-32">
          <button
            type="button"
            onClick={handleCreateNew}
            className={`px-4 py-2.5 rounded-xl font-semibold shadow-md transition-all duration-200 cursor-pointer hover:shadow-lg active:scale-[0.98] ${
              selectedId === null
                ? "bg-emd-primary text-emd-button-text ring-2 ring-emd-primary/40"
                : "bg-emd-accent text-emd-button-text hover:bg-emd-primary"
            }`}
          >
            + Create new
          </button>
          <Card title="Pipelines" padding="tight">
            <IngestionPipelineList
              pipelines={pipelines}
              selectedId={selectedId}
              onSelect={(p) => setSelectedId(p.id)}
              onLaunch={handleLaunch}
              onDelete={handleDelete}
              busyId={busyId}
              loading={loading}
            />
          </Card>
        </aside>

        {/* Right: a read-only view of the selected pipeline, or the create form
            when "create new" is active. */}
        <Card title={selectedPipeline ? "Pipeline details" : "New pipeline"}>
          <IngestionPipelineForm
            pipeline={selectedPipeline}
            providers={providers}
            datasets={datasets}
            chunkers={chunkers}
            onSubmit={handleSubmit}
            submitting={submitting}
            disabled={selectedPipeline !== null}
          />
        </Card>
      </div>
    </section>
  );
};

export default IngestionPipelinesPage;
