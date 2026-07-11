import { SelectOption } from "../common/Select";
import { DatasetSourceType } from "../datasets/types";
import { options as SIMILARITY_OPTIONS } from "../consts";
import { Provider } from "../providers/types";
import { ActorConfigMap, PluginFieldDef, SettingValue } from "./types";

// Chunker used when none is selected / recorded. Must match the backend
// registry's DEFAULT_CHUNKER (backend/plugins/chunkers/registry.py).
export const DEFAULT_CHUNKER = "text_markdown";

// Descriptor for a single (mock) actor setting field. The form renders the
// right control based on `type`. The optional `hidden` predicate receives the
// current values for ALL settings in that actor and returns true when this
// field should be hidden from the form (the value is still submitted as the
// default; see handleSubmit).
//
// The "provider" variant is special: its options are not embedded in the
// descriptor but resolved at render time from the providers list passed down
// through the component tree. The stored value is the provider's id string.
//
// The optional `description` is short help text rendered under the control to
// explain what the setting does (and its effect at the extremes).
export type SettingField =
  | { key: string; label: string; type: "text"; placeholder?: string; default: string; description?: string; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "number"; default: number; min?: number; description?: string; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "checkbox"; default: boolean; description?: string; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "select"; options: SelectOption[]; default: string; description?: string; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "provider"; default: string; description?: string; hidden?: (settings: Record<string, SettingValue>) => boolean };

// One stage of the ingestion pipeline. `name`/`description` come straight from
// the README's pipeline-flow section; `settings` are placeholder config for now.
// `note` is an optional extra hint shown under the description (used to surface
// the selected chunker's restrictions on the chunk_document actor).
export interface ActorDef {
  key: string;
  name: string;
  description: string;
  settings: SettingField[];
  note?: string;
}

const similaritySelectOptions: SelectOption[] = SIMILARITY_OPTIONS.map((o) => ({
  value: o.id,
  label: o.label,
}));

// ---- Actors shared by both chains --------------------------------------

// parse_source is plugin-backed (backend/plugins/parse_source): its settings
// are discovered from GET /actor-configs and injected by the form. The base
// def carries no settings.
const parseSource: ActorDef = {
  key: "parse_source",
  name: "parse_source",
  description:
    "Picks a parser by content type, extracts normalized text, saves the Document with metadata/hashes.",
  settings: [],
};

// The chunk_document actor's settings are NOT static: the chunker options and
// their per-chunker fields are discovered from the backend at runtime (GET
// /chunkers) and injected by the form via `chunkDocumentFields`. The base def
// carries no settings; the form replaces them for this actor key.
const chunkDocument: ActorDef = {
  key: "chunk_document",
  name: "chunk_document",
  description: "Splits text into chunks (via the selected chunker plugin) and persists discovered links.",
  settings: [],
};

const scheduleEmbeddings: ActorDef = {
  key: "schedule_embeddings",
  name: "schedule_embeddings",
  description: "Emits one embed job per chunk batch, then triggers link scheduling.",
  settings: [
    { key: "batchSize", label: "Batch size", type: "number", default: 64, min: 1 },
  ],
};

// embed_chunks' provider field is plugin-described (backend/plugins/embed_chunks
// "standard" strategy → a required provider_id field) and injected by the form
// via embedChunksFields; the base def carries no settings. The similarity field
// is appended there — it is a vector_store concern, not an embed plugin field.
const embedChunks: ActorDef = {
  key: "embed_chunks",
  name: "embed_chunks",
  description: "Embeds chunks and upserts vectors into Qdrant (point id = chunk id).",
  settings: [],
};

// The stored value of the embedding-provider field is the provider's id (see
// SettingControl's "provider" case). Used as a fallback when the backend config
// hasn't loaded yet so the required picker still renders.
const FALLBACK_PROVIDER_FIELD: SettingField = {
  key: "provider",
  label: "Embedding provider",
  type: "provider",
  default: "",
};

// Similarity is chosen inside embed_chunks but persisted under vector_store, so
// it is not an embed plugin field; it is appended to the actor's form here.
const SIMILARITY_FIELD: SettingField = {
  key: "similarity",
  label: "Similarity",
  type: "select",
  options: similaritySelectOptions,
  default: similaritySelectOptions[0]?.value ?? "cosine",
};

// ---- Web crawl chain ---------------------------------------------------

// validate_source is plugin-backed (backend/plugins/validate_source): the
// former UI "crawl_frontier_manager" step. Its settings (normalize_urls,
// dedup) are discovered from GET /actor-configs; the strategy (web/local) is
// resolved from the selected datasets' source types.
const validateSource: ActorDef = {
  key: "validate_source",
  name: "validate_source",
  description:
    "Dedup + origin gate; normalizes the source, creates a crawl_target (queued), enqueues fetch. Discovered links loop back here.",
  settings: [],
};

// fetch_source is plugin-backed (backend/plugins/fetch_source): its settings
// (web: verify_tls/timeout_seconds/allowed_content_types, local: file_glob)
// are discovered from GET /actor-configs; the strategy is resolved from the
// selected datasets' source types.
const fetchSource: ActorDef = {
  key: "fetch_source",
  name: "fetch_source",
  description:
    "Fetches the source (URL over TLS or local file), classifies failures, rejects unsupported content types, stores the raw fetch + provenance.",
  settings: [],
};

const scheduleDiscoveredLinks: ActorDef = {
  key: "schedule_discovered_links",
  name: "schedule_discovered_links",
  description:
    "Schedules persisted links back to the frontier, then marks the target processed.",
  settings: [
    { key: "followChildLinks", label: "Follow child links", type: "checkbox", default: true },
    { key: "followCrossDomain", label: "Follow cross-domain links", type: "checkbox", default: false },
    { key: "maxDepth", label: "Max depth", type: "number", default: 3, min: 1 },
  ],
};

// ---- Local XML file chain ----------------------------------------------

// filter_documents is plugin-backed (backend/plugins/filter_documents): its
// settings (enabled, keywords) are discovered from GET /actor-configs.
const filterDocuments: ActorDef = {
  key: "filter_documents",
  name: "filter_documents",
  description:
    "Extracts the document title and classifies it with a keyword filter; non-matching documents are skipped.",
  settings: [],
};

// Web crawl chain (README "Web crawl chain").
const WEB_CHAIN: ActorDef[] = [
  validateSource,
  fetchSource,
  parseSource,
  chunkDocument,
  scheduleEmbeddings,
  scheduleDiscoveredLinks,
  embedChunks,
];

// Local XML file chain (README "Local XML file chain"). The seed runner
// (add_file_source_job) is not a Dramatiq actor, so it isn't configurable here.
const FILE_CHAIN: ActorDef[] = [
  validateSource,
  fetchSource,
  filterDocuments,
  parseSource,
  chunkDocument,
  scheduleEmbeddings,
  embedChunks,
];

// Resolves the actor chain to render from the selected datasets' source types.
// When both source types are present the chains are merged (web order first,
// then any file-chain-only actors), de-duplicated by actor key.
export function resolveActorChain(sourceTypes: Set<DatasetSourceType>): ActorDef[] {
  const chain: ActorDef[] = [];
  const seen = new Set<string>();
  const add = (actors: ActorDef[]) => {
    for (const actor of actors) {
      if (seen.has(actor.key)) continue;
      seen.add(actor.key);
      chain.push(actor);
    }
  };
  if (sourceTypes.has("web")) add(WEB_CHAIN);
  if (sourceTypes.has("local")) add(FILE_CHAIN);
  return chain;
}

// Build SelectOption[] for the provider picker from the live provider list.
// Only embedding providers are relevant to the embed_chunks actor.
export function providerOptions(providers: Provider[]): SelectOption[] {
  return providers
    .filter((p) => p.modelType === "embedding")
    .map((p) => ({
      value: p.id,
      label: `${p.name} (${p.providerType})`,
    }));
}

// The default value for a single setting field.
export const settingDefault = (field: SettingField): SettingValue => field.default;

// ---- Dynamic fields (from discovered strategy plugins) ------------------

// Actors whose settings are discovered from the backend (GET /actor-configs)
// rather than hardcoded above. The value selects which strategy's fields to
// render: "bySourceType" resolves web/local from the selected datasets; a
// literal strategy name selects that single strategy. chunk_document is driven
// separately (its chunker is user-picked; see chunkDocumentFields) and
// embed_chunks stays hardcoded (its provider snapshot + vector-store similarity
// are cross-cutting concerns, not plain plugin fields).
const PLUGIN_ACTORS: Record<string, "bySourceType" | string> = {
  validate_source: "bySourceType",
  fetch_source: "bySourceType",
  parse_source: "content_type",
  filter_documents: "keyword",
};

// Whether an actor's settings come from GET /actor-configs.
export function isPluginActor(actorKey: string): boolean {
  return actorKey in PLUGIN_ACTORS;
}

// Resolve which strategy's fields to render for a plugin actor. web/local
// strategies are keyed by dataset source type; when both are present the web
// strategy wins (mirroring the merged chain's actor de-duplication).
function strategyForActor(
  actorKey: string,
  sourceTypes: Set<DatasetSourceType>
): string {
  const selector = PLUGIN_ACTORS[actorKey];
  if (selector !== "bySourceType") return selector;
  return sourceTypes.has("web") ? "web" : "local";
}

// Map one backend-declared plugin field to the form's SettingField. The field
// `key` is preserved verbatim (snake_case) so the submitted value round-trips
// into the actor's stored settings block. "provider_id" fields render with the
// live provider picker (same control as embed_chunks).
function toSettingField(field: PluginFieldDef): SettingField {
  switch (field.type) {
    case "number":
      return {
        key: field.key,
        label: field.label,
        type: "number",
        default: Number(field.default ?? 0),
        min: field.min ?? undefined,
      };
    case "checkbox":
      return {
        key: field.key,
        label: field.label,
        type: "checkbox",
        default: Boolean(field.default),
      };
    case "select":
      return {
        key: field.key,
        label: field.label,
        type: "select",
        options: (field.options ?? []).map((o) => ({
          value: o.value,
          label: o.label,
        })),
        default: String(field.default ?? ""),
      };
    case "provider_id":
      return {
        key: field.key,
        label: field.label,
        type: "provider",
        default: String(field.default ?? ""),
      };
    default:
      return {
        key: field.key,
        label: field.label,
        type: "text",
        default: String(field.default ?? ""),
        placeholder: field.placeholder ?? undefined,
      };
  }
}

// Build a plugin-backed actor's settings for the currently-selected datasets:
// the fields declared by its resolved strategy (web/local or the single
// strategy). Empty when the actor isn't plugin-backed or configs are still
// loading.
export function pluginActorFields(
  actorConfigs: ActorConfigMap,
  actorKey: string,
  sourceTypes: Set<DatasetSourceType>
): SettingField[] {
  if (!isPluginActor(actorKey)) return [];
  const strategies = actorConfigs[actorKey] ?? [];
  const wanted = strategyForActor(actorKey, sourceTypes);
  const strategy =
    strategies.find((s) => s.name === wanted) ?? strategies[0];
  return (strategy?.fields ?? []).map(toSettingField);
}

// The discovered chunkers are chunk_document's strategies in the unified
// GET /actor-configs payload (they share the strategy-config shape).
function chunkStrategies(actorConfigs: ActorConfigMap) {
  return actorConfigs["chunk_document"] ?? [];
}

// Build the chunk_document actor's settings for the currently-selected chunker:
// a "chunker" picker (options from the discovered plugins) followed by that
// chunker's own declared fields. Falls back to the default chunker when the
// selection is unknown (e.g. the list is still loading).
export function chunkDocumentFields(
  actorConfigs: ActorConfigMap,
  selected: string
): SettingField[] {
  const chunkers = chunkStrategies(actorConfigs);
  const chunkerField: SettingField = {
    key: "chunker",
    label: "Chunker",
    type: "select",
    options: chunkers.map((c) => ({ value: c.name, label: c.label || c.name })),
    default: DEFAULT_CHUNKER,
  };
  const active =
    chunkers.find((c) => c.name === selected) ??
    chunkers.find((c) => c.name === DEFAULT_CHUNKER);
  const fields = (active?.fields ?? []).map(toSettingField);
  return [chunkerField, ...fields];
}

// The selected chunker's free-text restrictions, for display under the actor
// description. Empty string when none / not found.
export function chunkerRestrictions(
  actorConfigs: ActorConfigMap,
  selected: string
): string {
  return (
    chunkStrategies(actorConfigs).find((c) => c.name === selected)
      ?.restrictions ?? ""
  );
}

// Build the embed_chunks actor's settings: the plugin-described provider field
// (from the "standard" strategy) followed by the similarity field. Falls back
// to a hardcoded provider picker while the backend config is still loading, so
// the required field always renders.
export function embedChunksFields(
  actorConfigs: ActorConfigMap
): SettingField[] {
  const strategies = actorConfigs["embed_chunks"] ?? [];
  const standard =
    strategies.find((s) => s.name === "standard") ?? strategies[0];
  const pluginFields = (standard?.fields ?? []).map(toSettingField);
  const providerFields =
    pluginFields.length > 0 ? pluginFields : [FALLBACK_PROVIDER_FIELD];
  return [...providerFields, SIMILARITY_FIELD];
}
