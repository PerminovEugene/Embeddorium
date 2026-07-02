import { SERVER_URL } from "../components/consts";
import {
  IngestionPipeline,
  IngestionPipelineFormValues,
  SettingValue,
} from "../components/ingestion-pipelines/types";
import { DEFAULT_CHUNKER } from "../components/ingestion-pipelines/actors";

// REST client for ingestion pipelines, backed by the `/pipeline-runs` API.
// A backend "pipeline run" is a self-contained snapshot of one dataset plus its
// provider/chunk config and a lifecycle status; the UI presents each run as an
// ingestion pipeline. Creating a run and launching it (publishing seed messages
// to the broker) are two separate calls, so a failed run can be relaunched.
//
// The create form allows several datasets, so creating fans out into one run
// per selected dataset, each carrying the same actor settings.

const BASE = `${SERVER_URL}/pipeline-runs`;
const JSON_HEADERS = { "Content-Type": "application/json" };

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

// Backend response shape: camelCase at the top level, snake_case inside the
// nested dataset/actor_configs snapshots (they are raw model dumps shaped by
// PipelineActorConfigs).
interface PipelineRunOut {
  id: string;
  name?: string | null;
  dataset: { id?: string; name?: string; source_type?: string; [k: string]: unknown };
  actorConfigs: {
    chunk_document?: {
      chunker?: string;
      settings?: Record<string, SettingValue>;
    };
    vector_store?: { collection?: string; similarity?: string };
    embed_chunks?: { provider?: { id?: string; model_name?: string; model?: string } };
    parse_source?: { parser?: string };
    schedule_embeddings?: { batch_size?: number };
    crawl_frontier_manager?: {
      normalize_urls?: boolean;
      dedup?: boolean;
      max_frontier_size?: number;
    };
    fetch_source?: {
      verify_tls?: boolean;
      timeout_seconds?: number;
      allowed_content_types?: string;
    };
    schedule_discovered_links?: {
      follow_child_links?: boolean;
      follow_cross_domain?: boolean;
      max_depth?: number;
    };
    fetch_file_source?: { glob?: string; dedup?: boolean };
    filter_documents?: { enabled?: boolean; keywords?: string };
  };
  status: IngestionPipeline["status"];
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string | null;
}

// Map a backend run onto the UI's IngestionPipeline shape. Actor settings are
// reconstructed from the stored snapshot (snake_case → the form's camelCase
// keys) so the read-only form/list can display exactly what the run was built
// with. Keys absent from a given run fall back to the form-field defaults.
function toPipeline(run: PipelineRunOut): IngestionPipeline {
  const cfg = run.actorConfigs;
  const chunk = cfg.chunk_document ?? {};
  const vector = cfg.vector_store ?? {};
  const provider = cfg.embed_chunks?.provider ?? {};
  const actorSettings: IngestionPipeline["actorSettings"] = {
    // The stored { chunker, settings } is flattened into the form's per-actor
    // scalar map ({ chunker, ...fieldValues }); the form re-nests it on submit.
    chunk_document: {
      chunker: chunk.chunker ?? DEFAULT_CHUNKER,
      ...(chunk.settings ?? {}),
    },
    embed_chunks: {
      providerId: provider.id ?? "",
      similarity: vector.similarity ?? "",
    },
  };
  if (cfg.parse_source) {
    actorSettings.parse_source = { parser: cfg.parse_source.parser ?? "auto" };
  }
  if (cfg.schedule_embeddings) {
    actorSettings.schedule_embeddings = {
      batchSize: cfg.schedule_embeddings.batch_size ?? 32,
    };
  }
  if (cfg.crawl_frontier_manager) {
    const c = cfg.crawl_frontier_manager;
    actorSettings.crawl_frontier_manager = {
      normalizeUrls: c.normalize_urls ?? true,
      dedup: c.dedup ?? true,
      maxFrontierSize: c.max_frontier_size ?? 10000,
    };
  }
  if (cfg.fetch_source) {
    const f = cfg.fetch_source;
    actorSettings.fetch_source = {
      verifyTls: f.verify_tls ?? true,
      timeoutSeconds: f.timeout_seconds ?? 30,
      allowedContentTypes: f.allowed_content_types ?? "",
    };
  }
  if (cfg.schedule_discovered_links) {
    const s = cfg.schedule_discovered_links;
    actorSettings.schedule_discovered_links = {
      followChildLinks: s.follow_child_links ?? true,
      followCrossDomain: s.follow_cross_domain ?? false,
      maxDepth: s.max_depth ?? 3,
    };
  }
  if (cfg.fetch_file_source) {
    actorSettings.fetch_file_source = {
      glob: cfg.fetch_file_source.glob ?? "*.xml",
      dedup: cfg.fetch_file_source.dedup ?? true,
    };
  }
  if (cfg.filter_documents) {
    actorSettings.filter_documents = {
      enabled: cfg.filter_documents.enabled ?? true,
      keywords: cfg.filter_documents.keywords ?? "",
    };
  }
  return {
    id: run.id,
    // The run's own name; fall back to the dataset name for legacy rows.
    name: run.name?.trim() || run.dataset.name || "(unnamed dataset)",
    datasetIds: run.dataset.id ? [run.dataset.id] : [],
    actorSettings,
    status: run.status,
    collection: vector.collection ?? "",
    embedModel: provider.model_name ?? provider.model ?? "",
    createdAt: run.createdAt,
  };
}

export async function fetchIngestionPipelines(): Promise<IngestionPipeline[]> {
  const runs = await parse<PipelineRunOut[]>(await fetch(BASE));
  return runs.map(toPipeline);
}

// Re-nest the flat chunk_document form block ({ chunker, ...fieldValues }) into
// the server's stored shape ({ chunker, settings: {...fieldValues} }). The
// server stores settings verbatim (no camel/snake conversion), and the field
// keys are already the snake_case keys the chunker declared, so they pass
// through untouched. Other actors are forwarded unchanged.
function reshapeActorSettings(
  actorSettings: IngestionPipelineFormValues["actorSettings"]
): Record<string, unknown> {
  const chunk = actorSettings["chunk_document"];
  if (!chunk) return actorSettings;
  const { chunker, ...fields } = chunk;
  return {
    ...actorSettings,
    chunk_document: {
      chunker: String(chunker ?? DEFAULT_CHUNKER),
      settings: fields,
    },
  };
}

// Build the create body for a single dataset. Per-actor settings are forwarded
// keyed by actor; the server resolves them into a typed PipelineActorConfigs
// snapshot and fills any gaps with defaults. The chunk_document block is
// re-nested into { chunker, settings }. embed_chunks.providerId is required
// (validated server-side).
function toCreateBody(datasetId: string, values: IngestionPipelineFormValues) {
  return {
    name: values.name,
    datasetId,
    actorSettings: reshapeActorSettings(values.actorSettings),
  };
}

// Creating fans out into one run per selected dataset. Returns the created
// pipelines; callers typically refetch the list afterwards.
export async function createIngestionPipelines(
  values: IngestionPipelineFormValues
): Promise<IngestionPipeline[]> {
  if (values.datasetIds.length === 0) {
    throw new Error("Select at least one dataset");
  }
  const providerId = String(values.actorSettings["embed_chunks"]?.["providerId"] ?? "");
  if (!providerId) {
    throw new Error("Select an embedding provider");
  }
  const created: IngestionPipeline[] = [];
  for (const datasetId of values.datasetIds) {
    const run = await parse<PipelineRunOut>(
      await fetch(BASE, {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify(toCreateBody(datasetId, values)),
      })
    );
    created.push(toPipeline(run));
  }
  return created;
}

// Launch (or relaunch) a pipeline: publishes its seed messages to the broker
// and flips it to "running". Safe to call again on a failed run.
export async function launchIngestionPipeline(
  id: string
): Promise<IngestionPipeline> {
  return toPipeline(
    await parse<PipelineRunOut>(
      await fetch(`${BASE}/${id}/launch`, { method: "POST" })
    )
  );
}

export async function deleteIngestionPipeline(id: string): Promise<void> {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Delete failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
}
