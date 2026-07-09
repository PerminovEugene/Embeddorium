import { SearchDetail, SearchSummary } from "../../api/searches";

// Pure helpers that turn the selected searches' stored results into the rows
// the comparison table renders. Kept out of the components so the grouping
// logic is testable and the table stays presentational.

export type ComparisonView = "chunks" | "documents" | "ranks";

// One hit flattened out of a selected search, carrying enough context to be
// grouped by chunk, by document or by rank.
export interface CombinedHit {
  searchId: string;
  searchName: string;
  // Stable per selected search (selection order); drives the color dot.
  colorIndex: number;
  // Index of the hit in its search's stored results. Results are persisted
  // already sorted by score, so 0 = that search's best hit.
  rank: number;
  score: number | null;
  chunkKey: string;
  chunkText: string;
  documentKey: string;
  documentId: string | null;
  sourceUrl: string | null;
}

// One table row: a chunk plus every search hit that returned it.
export interface ChunkRow {
  chunkKey: string;
  chunkText: string;
  documentKey: string;
  documentId: string | null;
  sourceUrl: string | null;
  // Sorted by rank so the stacked per-search entries read best-first.
  hits: CombinedHit[];
  bestRank: number;
}

export interface DocumentGroup {
  documentKey: string;
  documentId: string | null;
  sourceUrl: string | null;
  rows: ChunkRow[];
}

export interface RankGroup {
  rank: number;
  hits: CombinedHit[];
}

// Display label for a saved search. Run names repeat across launches, so the
// timestamp is appended to keep entries distinguishable.
export function searchLabel(s: SearchSummary): string {
  const name = s.runName || s.pipelineId.slice(0, 8);
  const time = s.createdAt ? new Date(s.createdAt).toLocaleString() : "";
  return time ? `${name} · ${time}` : name;
}

// Short human label for a document: last URL path segment, falling back to
// the hostname, then to a shortened document id.
export function documentLabel(
  sourceUrl: string | null,
  documentId: string | null,
): string {
  if (sourceUrl) {
    try {
      const url = new URL(sourceUrl);
      const segment = url.pathname.split("/").filter(Boolean).pop();
      return segment ?? url.hostname;
    } catch {
      return sourceUrl;
    }
  }
  return documentId ? `document ${documentId.slice(0, 8)}` : "Unknown document";
}

// Identity of a chunk across searches. Searches on the same pipeline run
// return the same chunkId for the same chunk; when chunkId is missing we fall
// back to (document, position) and finally to a per-hit key so unidentifiable
// hits never merge with each other.
function chunkKeyOf(
  hit: { chunkId: string | null; documentId: string | null; chunkIndex: number | null },
  fallback: string,
): string {
  if (hit.chunkId) return hit.chunkId;
  if (hit.documentId != null && hit.chunkIndex != null)
    return `${hit.documentId}#${hit.chunkIndex}`;
  return fallback;
}

export function flattenHits(details: SearchDetail[]): CombinedHit[] {
  return details.flatMap((detail, searchIdx) =>
    detail.results.map((hit, rank) => ({
      searchId: detail.id,
      searchName: searchLabel(detail),
      colorIndex: searchIdx,
      rank,
      score: hit.score ?? null,
      chunkKey: chunkKeyOf(hit, `${detail.id}:${rank}`),
      chunkText: hit.chunkText ?? "",
      documentKey: hit.sourceUrl ?? hit.documentId ?? "unknown",
      documentId: hit.documentId ?? null,
      sourceUrl: hit.sourceUrl ?? null,
    })),
  );
}

// Deduplicate hits into one row per chunk, best (lowest) rank first.
export function buildChunkRows(hits: CombinedHit[]): ChunkRow[] {
  const byChunk = new Map<string, ChunkRow>();
  for (const hit of hits) {
    const row = byChunk.get(hit.chunkKey);
    if (row) {
      row.hits.push(hit);
      row.bestRank = Math.min(row.bestRank, hit.rank);
    } else {
      byChunk.set(hit.chunkKey, {
        chunkKey: hit.chunkKey,
        chunkText: hit.chunkText,
        documentKey: hit.documentKey,
        documentId: hit.documentId,
        sourceUrl: hit.sourceUrl,
        hits: [hit],
        bestRank: hit.rank,
      });
    }
  }
  const rows = [...byChunk.values()];
  for (const row of rows) row.hits.sort((a, b) => a.rank - b.rank);
  return rows.sort((a, b) => a.bestRank - b.bestRank);
}

// Group chunk rows by their source document, ordered by each document's best
// rank so the most relevant documents come first.
export function buildDocumentGroups(hits: CombinedHit[]): DocumentGroup[] {
  const groups = new Map<string, DocumentGroup>();
  for (const row of buildChunkRows(hits)) {
    const group = groups.get(row.documentKey);
    if (group) {
      group.rows.push(row);
    } else {
      groups.set(row.documentKey, {
        documentKey: row.documentKey,
        documentId: row.documentId,
        sourceUrl: row.sourceUrl,
        rows: [row],
      });
    }
  }
  // buildChunkRows already yields rows best-rank first, so the first row of
  // each group is that document's best hit — group order follows from it.
  return [...groups.values()];
}

// Group hits by rank: all rank-0 hits (one per search), then rank-1, etc.
// Within a rank, hits keep selection order so columns line up across groups.
export function buildRankGroups(hits: CombinedHit[]): RankGroup[] {
  const byRank = new Map<number, RankGroup>();
  for (const hit of hits) {
    const group = byRank.get(hit.rank);
    if (group) {
      group.hits.push(hit);
    } else {
      byRank.set(hit.rank, { rank: hit.rank, hits: [hit] });
    }
  }
  const groups = [...byRank.values()].sort((a, b) => a.rank - b.rank);
  for (const group of groups)
    group.hits.sort((a, b) => a.colorIndex - b.colorIndex);
  return groups;
}
