// An ingestion pipeline ties together a dataset and configures the chain of
// pipeline actors that ingest it. The embedding provider is selected inside the
// embed_chunks actor config (actorSettings["embed_chunks"]["providerId"]) rather
// than at the root level — see actors.ts for the "provider" field type. It is
// backed by a `/pipeline-runs` row (see api/ingestionPipelines.ts).

// A single setting value. The value space is kept deliberately small.
export type SettingValue = string | number | boolean;

// Per-actor settings, keyed by actor key then by setting key.
export type ActorSettings = Record<string, Record<string, SettingValue>>;

// Lifecycle state of a pipeline run, mirroring the backend status enum.
export type PipelineStatus = "pending" | "running" | "completed" | "failed";

export interface IngestionPipeline {
  id: string;
  name: string;
  // Datasets ingested by the pipeline.
  datasetIds: string[];
  // Per-actor configuration. embed_chunks.providerId holds the chosen
  // embedding provider id.
  actorSettings: ActorSettings;
  // Lifecycle status; "pending" until launched.
  status: PipelineStatus;
  // Display-only fields pulled from the backend run snapshot.
  collection?: string;
  embedModel?: string;
  createdAt?: string | null;
}

// A single flat shape backing the form. Mirrors IngestionPipeline without its
// server-assigned id.
export interface IngestionPipelineFormValues {
  name: string;
  datasetIds: string[];
  actorSettings: ActorSettings;
}
