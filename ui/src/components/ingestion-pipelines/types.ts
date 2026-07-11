// An ingestion pipeline ties together a dataset and configures the chain of
// pipeline actors that ingest it. The embedding provider is selected inside the
// embed_chunks actor config (actorSettings["embed_chunks"]["provider"]) rather
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
  // Per-actor configuration. embed_chunks.provider holds the chosen
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

// ---- Actor strategy plugins (GET /actor-configs) -----------------------
// Every configurable actor is backed by strategy plugins under
// backend/plugins/<actor>. The server discovers them and exposes, per actor,
// the available strategies plus each strategy's declared settings fields, so
// the form can render each actor's config dynamically instead of hardcoding it.

// One field a strategy declares. Superset of ChunkerFieldDef: it also carries
// `required` and the "provider_id" type (a provider picker). Field `key` values
// are snake_case and round-trip verbatim into the actor's stored settings.
export interface PluginFieldDef {
  key: string;
  label: string;
  type: "text" | "number" | "checkbox" | "select" | "provider_id";
  default: SettingValue | null;
  min?: number | null;
  max?: number | null;
  options?: { value: string; label: string }[] | null;
  placeholder?: string | null;
  required?: boolean;
}

// One strategy plugin's static, UI-facing metadata.
export interface StrategyConfig {
  name: string;
  label: string;
  description: string;
  // Free-text usage constraints. May be empty.
  restrictions: string;
  fields: PluginFieldDef[];
}

// Every strategy available for one plugin-backed actor.
export interface ActorConfig {
  // Actor key; matches the stored PipelineActorConfigs snapshot key.
  actor: string;
  strategies: StrategyConfig[];
}

// Lookup of actor key -> its available strategies, built from GET /actor-configs.
export type ActorConfigMap = Record<string, StrategyConfig[]>;
