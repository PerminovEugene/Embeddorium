import { SERVER_URL } from "../components/consts";

// REST client for the persisted-search history (GET /searches). Every /search
// launch is saved server-side; the comparison page lists those saved searches
// and loads the stored results of the ones the user selects.

const BASE = `${SERVER_URL}/searches`;

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

// One saved search launch, without its hits (mirrors SearchSummaryOut).
export interface SearchSummary {
  id: string;
  pipelineId: string;
  runName: string;
  datasetName: string;
  inputText: string;
  topK: number | null;
  searchMethod: string;
  resultCount: number;
  createdAt: string | null;
}

// One stored hit, as persisted by the /search endpoint. Hits keep the order
// they were returned in (sorted by score at search time), so a hit's index in
// `results` is its rank within that search.
export interface SearchResultHit {
  score: number | null;
  chunkId: string | null;
  documentId: string | null;
  // Position of the chunk within its source document (not the rank).
  chunkIndex: number | null;
  chunkText: string | null;
  sourceUrl: string | null;
}

export interface SearchDetail extends SearchSummary {
  results: SearchResultHit[];
}

// List saved searches, newest first.
export async function fetchSearchSummaries(): Promise<SearchSummary[]> {
  return parse<SearchSummary[]>(await fetch(BASE));
}

// Load one saved search including its stored results.
export async function fetchSearch(id: string): Promise<SearchDetail> {
  return parse<SearchDetail>(await fetch(`${BASE}/${id}`));
}
