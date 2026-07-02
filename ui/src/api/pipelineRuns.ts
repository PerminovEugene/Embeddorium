import { SERVER_URL } from "../components/consts";
import { PipelineStatus } from "../components/ingestion-pipelines/types";

// REST client for the pipeline-runs observability surface. Distinct from
// ingestionPipelines.ts (which maps runs onto the heavier IngestionPipeline
// shape for the creation/management flow); this module needs only the summary
// fields and the new /targets sub-resource.

const BASE = `${SERVER_URL}/pipeline-runs`;

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

// Lightweight run summary — just the fields the Pipeline Runs page needs.
// The backend returns more (dataset, actorConfigs); extra fields are ignored.
export interface PipelineRunSummary {
  id: string;
  name: string | null;
  status: PipelineStatus;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string | null;
}

// One crawl target row, mirroring PipelineRunTargetOut on the server.
// Field names are camelCase (the backend alias_generator converts snake_case).
export interface PipelineRunTarget {
  id: string;
  url: string;
  normalizedUrl: string;
  status: string;
  skipReason: string | null;
  error: string | null;
  chunkCount: number;
  documentId: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

// Paginated response from GET /pipeline-runs/{id}/targets.
export interface PipelineRunTargetsPage {
  items: PipelineRunTarget[];
  total: number;
  limit: number;
  offset: number;
}

// The raw backend shape we actually read off the wire (superset of
// PipelineRunSummary — extra keys are silently ignored at runtime).
interface _RawRunOut {
  id: string;
  name?: string | null;
  status: PipelineStatus;
  startedAt: string | null;
  finishedAt: string | null;
  createdAt: string | null;
}

function toSummary(raw: _RawRunOut): PipelineRunSummary {
  return {
    id: raw.id,
    name: raw.name ?? null,
    status: raw.status,
    startedAt: raw.startedAt,
    finishedAt: raw.finishedAt,
    createdAt: raw.createdAt,
  };
}

// List every pipeline run, newest first (mirrors GET /pipeline-runs ordering).
export async function fetchPipelineRunSummaries(): Promise<PipelineRunSummary[]> {
  const raw = await parse<_RawRunOut[]>(await fetch(BASE));
  return raw.map(toSummary);
}

// Fetch a single run's current info (used for polling status updates).
export async function fetchPipelineRun(id: string): Promise<PipelineRunSummary> {
  const raw = await parse<_RawRunOut>(await fetch(`${BASE}/${id}`));
  return toSummary(raw);
}

// Paginated list of processed files/URLs for the given run.
export async function fetchPipelineRunTargets(
  id: string,
  { limit, offset }: { limit: number; offset: number }
): Promise<PipelineRunTargetsPage> {
  const url = `${BASE}/${id}/targets?limit=${limit}&offset=${offset}`;
  return parse<PipelineRunTargetsPage>(await fetch(url));
}
