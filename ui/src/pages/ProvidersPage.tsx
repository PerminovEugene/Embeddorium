import { useEffect, useMemo, useState } from "react";
import {
  createProvider,
  deleteProvider,
  fetchProviderConfigs,
  fetchProviders,
} from "../api/providers";
import ProviderList from "../components/providers/ProviderList";
import ProviderForm from "../components/providers/ProviderForm";
import {
  Provider,
  ProviderFormValues,
  ProviderTypeConfig,
} from "../components/providers/types";
import Card from "../components/common/Card";

const ProvidersPage = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [providerConfigs, setProviderConfigs] = useState<ProviderTypeConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // null selection === "create new".
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([fetchProviders(), fetchProviderConfigs()])
      .then(([providerData, configData]) => {
        if (active) {
          setProviders(providerData);
          setProviderConfigs(configData);
        }
      })
      .catch((err) => {
        console.error("Failed to load providers:", err);
        if (active) setError("Failed to load providers");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const selectedProvider = useMemo(
    () => providers.find((p) => p.id === selectedId) ?? null,
    [providers, selectedId],
  );

  const handleCreateNew = () => setSelectedId(null);

  const handleSubmit = async (values: ProviderFormValues) => {
    if (selectedProvider) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await createProvider(values);
      // list endpoint returns newest first, so prepend.
      setProviders((prev) => [created, ...prev]);
      setSelectedId(created.id);
    } catch (err) {
      console.error("Failed to save provider:", err);
      setError("Failed to save provider");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedProvider) return;
    if (!window.confirm(`Delete provider "${selectedProvider.name}"?`)) return;
    setSubmitting(true);
    setError(null);
    try {
      await deleteProvider(selectedProvider.id);
      setProviders((prev) => prev.filter((p) => p.id !== selectedProvider.id));
      setSelectedId(null);
    } catch (err) {
      console.error("Failed to delete provider:", err);
      setError("Failed to delete provider");
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
            <ProviderList
              providers={providers}
              providerConfigs={providerConfigs}
              selectedId={selectedId}
              onSelect={(p) => setSelectedId(p.id)}
              loading={loading}
            />
          </Card>
        </aside>

        {/* Right: form prefilled by the selection, or empty for "create new". */}
        <Card title={selectedProvider ? "Provider details" : "New provider"}>
          <ProviderForm
            provider={selectedProvider}
            providerConfigs={providerConfigs}
            onSubmit={handleSubmit}
            onDelete={handleDelete}
            submitting={submitting}
          />
        </Card>
      </div>
    </section>
  );
};

export default ProvidersPage;
