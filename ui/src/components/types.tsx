import { Similarity } from "./consts";

export interface Variable {
  input: string;
  id: string;
}

export interface VariableGroup {
  variables: Variable[];
  id: string;
}

export interface Input {
  text: string;
  id: string;
}

export interface ValidationErrors {
  embeddingModelName?: string;
  ollamaPort?: string;
  source?: string;
  candidates?: string;
}

export interface Model {
  name: string;
  id: string;
}

export interface FormState {
  sourceVariableGroups: VariableGroup[];
  sourceInputs: Input[];

  candidateVariableGroups: VariableGroup[];
  candidateInputs: Input[];

  models: Model[];
}

export interface Match {
  source_id: string;
  candidate_id: string;

  sourceText: string;
  candidateText: string;
  model: string;
  [key in Similarity]?: number;
}

export type SourceType = "manual" | "db";

// A recorded ingestion pipeline run, as listed by GET /pipeline-runs. Selecting
// one in DB-search mode supplies the collection to search and the embedding
// provider/model the query must be embedded with (so they always match what the
// collection was built with).
export interface PipelineRun {
  id: string;
  group: string;
  sourceType: string;
  collection: string;
  embedProvider: string;
  embedModel: string;
  similarity: string;
  chunkSize: number;
  chunkOverlap: number;
  createdAt: string | null;
}

// A nearest-neighbour hit returned by /search (DB source mode), carrying the
// Qdrant score plus the chunk/document "batch info" joined from Postgres.
export interface DbMatch {
  source_id: string;
  queryText: string;
  score: number;
  model: string;
  chunkId: string | null;
  documentId: string | null;
  chunkIndex: number | null;
  group: string | null;
  chunkText: string | null;
  sourceUrl: string | null;
}
