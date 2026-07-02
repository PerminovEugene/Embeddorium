import { useEffect, useMemo, useState } from "react";
import {
  createDataset,
  deleteDataset,
  fetchDatasets,
  updateDataset,
} from "../api/datasets";
import DatasetList from "../components/datasets/DatasetList";
import DatasetForm from "../components/datasets/DatasetForm";
import { Dataset, DatasetFormValues } from "../components/datasets/types";
import Card from "../components/common/Card";

const DatasetsPage = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // null selection === "create new".
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetchDatasets()
      .then((data) => {
        if (active) setDatasets(data);
      })
      .catch((err) => {
        console.error("Failed to load datasets:", err);
        if (active) setError("Failed to load datasets");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const selectedDataset = useMemo(
    () => datasets.find((d) => d.id === selectedId) ?? null,
    [datasets, selectedId],
  );

  const handleCreateNew = () => setSelectedId(null);

  const handleSubmit = async (values: DatasetFormValues) => {
    setSubmitting(true);
    setError(null);
    try {
      if (selectedDataset) {
        const updated = await updateDataset(selectedDataset.id, values);
        setDatasets((prev) =>
          prev.map((d) => (d.id === updated.id ? updated : d)),
        );
      } else {
        const created = await createDataset(values);
        // list endpoint returns newest first, so prepend.
        setDatasets((prev) => [created, ...prev]);
        setSelectedId(created.id);
      }
    } catch (err) {
      console.error("Failed to save dataset:", err);
      setError("Failed to save dataset");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedDataset) return;
    if (!window.confirm(`Delete dataset "${selectedDataset.name}"?`)) return;
    setSubmitting(true);
    setError(null);
    try {
      await deleteDataset(selectedDataset.id);
      setDatasets((prev) => prev.filter((d) => d.id !== selectedDataset.id));
      setSelectedId(null);
    } catch (err) {
      console.error("Failed to delete dataset:", err);
      setError("Failed to delete dataset");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section>
      {error && (
        <p className="mb-6 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3 shadow-sm">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-[20rem_1fr] gap-6 items-start">
        {/* Left: list with "create new" action above it. */}
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
          <Card padding="tight">
            <DatasetList
              datasets={datasets}
              selectedId={selectedId}
              onSelect={(d) => setSelectedId(d.id)}
              loading={loading}
            />
          </Card>
        </aside>

        {/* Right: form prefilled by the selection, or empty for "create new". */}
        <Card title={selectedDataset ? "Edit dataset" : "New dataset"}>
          <DatasetForm
            dataset={selectedDataset}
            onSubmit={handleSubmit}
            onDelete={handleDelete}
            submitting={submitting}
          />
        </Card>
      </div>
    </section>
  );
};

export default DatasetsPage;
