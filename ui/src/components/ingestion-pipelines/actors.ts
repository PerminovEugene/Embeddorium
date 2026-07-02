import { SelectOption } from "../common/Select";
import { DatasetSourceType } from "../datasets/types";
import { options as SIMILARITY_OPTIONS } from "../consts";
import { Provider } from "../providers/types";
import { ChunkerConfig, ChunkerFieldDef, SettingValue } from "./types";

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
export type SettingField =
  | { key: string; label: string; type: "text"; placeholder?: string; default: string; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "number"; default: number; min?: number; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "checkbox"; default: boolean; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "select"; options: SelectOption[]; default: string; hidden?: (settings: Record<string, SettingValue>) => boolean }
  | { key: string; label: string; type: "provider"; default: string; hidden?: (settings: Record<string, SettingValue>) => boolean };

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

const parseSource: ActorDef = {
  key: "parse_source",
  name: "parse_source",
  description:
    "Picks a parser by content type, extracts normalized text, saves the Document with metadata/hashes.",
  settings: [
    {
      key: "parser",
      label: "Parser",
      type: "select",
      options: [
        { value: "auto", label: "Auto (by content type)" },
        { value: "html", label: "HTML → Markdown" },
        { value: "xml", label: "XML" },
        { value: "pdf", label: "PDF" },
      ],
      default: "auto",
    },
  ],
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

const embedChunks: ActorDef = {
  key: "embed_chunks",
  name: "embed_chunks",
  description: "Embeds chunks and upserts vectors into Qdrant (point id = chunk id).",
  settings: [
    // "provider" is resolved at render time from the providers list (see
    // ActorSection / SettingControl). The stored value is the provider's id.
    {
      key: "providerId",
      label: "Embedding provider",
      type: "provider",
      default: "",
    },
    {
      key: "similarity",
      label: "Similarity",
      type: "select",
      options: similaritySelectOptions,
      default: similaritySelectOptions[0]?.value ?? "cosine",
    },
  ],
};

// ---- Web crawl chain ---------------------------------------------------

const crawlFrontierManager: ActorDef = {
  key: "crawl_frontier_manager",
  name: "crawl_frontier_manager",
  description:
    "Dedup gate; normalizes the URL, creates a crawl_target (queued), enqueues fetch. Discovered links loop back here.",
  settings: [
    { key: "normalizeUrls", label: "Normalize URLs", type: "checkbox", default: true },
    { key: "dedup", label: "Dedup by normalized URL", type: "checkbox", default: true },
    { key: "maxFrontierSize", label: "Max frontier size", type: "number", default: 10000, min: 1 },
  ],
};

const fetchSource: ActorDef = {
  key: "fetch_source",
  name: "fetch_source",
  description:
    "Fetches the URL (TLS verified), classifies failures, rejects unsupported content types, stores the raw fetch + provenance.",
  settings: [
    { key: "verifyTls", label: "Verify TLS", type: "checkbox", default: true },
    { key: "timeoutSeconds", label: "Timeout (seconds)", type: "number", default: 30, min: 1 },
    {
      // Empty means "no extra restriction" — the parser registry decides what
      // is supported. A non-empty list further narrows the accepted types.
      key: "allowedContentTypes",
      label: "Allowed content types",
      type: "text",
      placeholder: "Any supported (e.g. text/html, text/xml)",
      default: "",
    },
  ],
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

const fetchFileSource: ActorDef = {
  key: "fetch_file_source",
  name: "fetch_file_source",
  description:
    "Normalizes the path to file://<abs_path>, dedups against an already-queued target, reads the file, stores raw content as a SourceFetch.",
  settings: [
    { key: "glob", label: "File glob", type: "text", placeholder: "*.xml", default: "*.xml" },
    { key: "dedup", label: "Dedup by normalized path", type: "checkbox", default: true },
  ],
};

const filterDocuments: ActorDef = {
  key: "filter_documents",
  name: "filter_documents",
  description:
    "Extracts the document title and classifies it with a keyword filter; non-matching documents are skipped.",
  settings: [
    { key: "enabled", label: "Enabled", type: "checkbox", default: true },
    {
      // Empty means no keyword filtering — every document passes through. A
      // non-empty list keeps only documents matching one of the keywords.
      key: "keywords",
      label: "Keywords",
      type: "text",
      placeholder: "keyword1, keyword2",
      default: "",
    },
  ],
};

// Web crawl chain (README "Web crawl chain").
const WEB_CHAIN: ActorDef[] = [
  crawlFrontierManager,
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
  fetchFileSource,
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

// ---- Dynamic chunk_document fields (from discovered chunkers) -----------

// Map one backend-declared chunker field to the form's SettingField. The
// field `key` is preserved verbatim (snake_case) so the submitted value
// round-trips into the server's ChunkDocumentSettings.settings.
function toSettingField(field: ChunkerFieldDef): SettingField {
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

// Build the chunk_document actor's settings for the currently-selected chunker:
// a "chunker" picker (options from the discovered plugins) followed by that
// chunker's own declared fields. Falls back to the default chunker when the
// selection is unknown (e.g. the list is still loading).
export function chunkDocumentFields(
  chunkers: ChunkerConfig[],
  selected: string
): SettingField[] {
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
  chunkers: ChunkerConfig[],
  selected: string
): string {
  return chunkers.find((c) => c.name === selected)?.restrictions ?? "";
}
