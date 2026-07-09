import { useMemo, useState } from "react";
import { SEARCH_COLORS } from "./colors";
import {
  buildChunkRows,
  buildDocumentGroups,
  buildRankGroups,
  ChunkRow,
  CombinedHit,
  ComparisonView,
  documentLabel,
} from "./combine";

interface ComparisonTableProps {
  hits: CombinedHit[];
  view: ComparisonView;
}

const HEADER_ROW = (
  <tr className="border-b border-emd-border/15 text-left text-xs uppercase tracking-wide text-emd-placeholder">
    <th className="py-3 pr-4 font-semibold first:pl-1">Search</th>
    <th className="py-3 pr-4 font-semibold whitespace-nowrap"># in search</th>
    <th className="py-3 pr-4 font-semibold">Document</th>
    <th className="py-3 pl-4 font-semibold last:pr-1">Chunk</th>
  </tr>
);

function formatScore(score: number | null): string {
  return score == null ? "" : ` (${score.toFixed(3)})`;
}

// Name of one search with its color dot, as stacked in the "Search" column.
function SearchChip({ hit }: { hit: CombinedHit }) {
  return (
    <span className="flex items-center gap-2 leading-6">
      <span
        aria-hidden
        className={`h-2.5 w-2.5 shrink-0 rounded-full ${SEARCH_COLORS[hit.colorIndex % SEARCH_COLORS.length]}`}
      />
      <span className="truncate" title={hit.searchName}>
        {hit.searchName}
      </span>
    </span>
  );
}

// Link to the source document (opens in a new tab), or a plain label when the
// document has no URL.
function DocumentCell({
  sourceUrl,
  documentId,
}: {
  sourceUrl: string | null;
  documentId: string | null;
}) {
  const label = documentLabel(sourceUrl, documentId);
  if (!sourceUrl) return <span className="text-emd-text/70">{label}</span>;
  return (
    <a
      href={sourceUrl}
      target="_blank"
      rel="noreferrer"
      title={sourceUrl}
      className="text-emd-primary underline decoration-emd-primary/40 underline-offset-2 hover:decoration-emd-primary break-all"
    >
      {label}
    </a>
  );
}

// Chunk text, clamped to a few lines; click toggles the full text.
function ChunkTextCell({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  if (!text) return <span className="text-emd-placeholder">—</span>;
  return (
    <button
      type="button"
      onClick={() => setExpanded((v) => !v)}
      title={expanded ? "Click to collapse" : "Click to expand"}
      className={`block w-full whitespace-pre-wrap text-left text-xs leading-5 text-emd-text/90 ${
        expanded ? "" : "line-clamp-3"
      }`}
    >
      {text}
    </button>
  );
}

// One deduplicated chunk row: the per-search chips and their ranks are
// stacked line-by-line in the same order, so name and rank read as pairs.
function ChunkRowTr({ row }: { row: ChunkRow }) {
  return (
    <tr className="text-emd-text align-top transition-colors hover:bg-emd-primary/5">
      <td className="py-3 pr-4 first:pl-1 max-w-[16rem]">
        {row.hits.map((hit) => (
          <SearchChip key={`${hit.searchId}:${hit.rank}`} hit={hit} />
        ))}
      </td>
      <td className="py-3 pr-4 whitespace-nowrap tabular-nums">
        {row.hits.map((hit) => (
          <span key={`${hit.searchId}:${hit.rank}`} className="block leading-6">
            #{hit.rank + 1}
            <span className="text-xs text-emd-placeholder">
              {formatScore(hit.score)}
            </span>
          </span>
        ))}
      </td>
      <td className="py-3 pr-4 max-w-[14rem] text-xs">
        <DocumentCell sourceUrl={row.sourceUrl} documentId={row.documentId} />
      </td>
      <td className="py-3 pl-4 last:pr-1">
        <ChunkTextCell text={row.chunkText} />
      </td>
    </tr>
  );
}

// Full-width separator row used as the section header in grouped views.
function GroupHeaderTr({ children }: { children: React.ReactNode }) {
  return (
    <tr className="bg-emd-accent/10">
      <td colSpan={4} className="px-1 py-2 text-xs font-semibold uppercase tracking-wide text-emd-text/70">
        {children}
      </td>
    </tr>
  );
}

// Combined results of the selected searches, rendered per the chosen view:
// "chunks" — one row per distinct chunk, listing every search that hit it;
// "documents" — the same rows, sectioned by source document;
// "ranks" — one row per hit, sectioned by rank (all #1 hits, then #2, …).
const ComparisonTable: React.FC<ComparisonTableProps> = ({ hits, view }) => {
  const chunkRows = useMemo(
    () => (view === "chunks" ? buildChunkRows(hits) : []),
    [hits, view],
  );
  const documentGroups = useMemo(
    () => (view === "documents" ? buildDocumentGroups(hits) : []),
    [hits, view],
  );
  const rankGroups = useMemo(
    () => (view === "ranks" ? buildRankGroups(hits) : []),
    [hits, view],
  );

  if (hits.length === 0) {
    return (
      <p className="text-sm text-emd-placeholder">
        The selected searches have no stored results.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>{HEADER_ROW}</thead>

        {view === "chunks" && (
          <tbody className="divide-y divide-emd-border/10">
            {chunkRows.map((row) => (
              <ChunkRowTr key={row.chunkKey} row={row} />
            ))}
          </tbody>
        )}

        {view === "documents" &&
          documentGroups.map((group) => (
            <tbody
              key={group.documentKey}
              className="divide-y divide-emd-border/10"
            >
              <GroupHeaderTr>
                <DocumentCell
                  sourceUrl={group.sourceUrl}
                  documentId={group.documentId}
                />
                <span className="ml-2 font-normal normal-case text-emd-placeholder">
                  {group.rows.length}{" "}
                  {group.rows.length === 1 ? "chunk" : "chunks"}
                </span>
              </GroupHeaderTr>
              {group.rows.map((row) => (
                <ChunkRowTr key={row.chunkKey} row={row} />
              ))}
            </tbody>
          ))}

        {view === "ranks" &&
          rankGroups.map((group) => (
            <tbody key={group.rank} className="divide-y divide-emd-border/10">
              <GroupHeaderTr>Rank #{group.rank + 1}</GroupHeaderTr>
              {group.hits.map((hit) => (
                <tr
                  key={`${hit.searchId}:${hit.rank}`}
                  className="text-emd-text align-top transition-colors hover:bg-emd-primary/5"
                >
                  <td className="py-3 pr-4 first:pl-1 max-w-[16rem]">
                    <SearchChip hit={hit} />
                  </td>
                  <td className="py-3 pr-4 whitespace-nowrap tabular-nums">
                    #{hit.rank + 1}
                    <span className="text-xs text-emd-placeholder">
                      {formatScore(hit.score)}
                    </span>
                  </td>
                  <td className="py-3 pr-4 max-w-[14rem] text-xs">
                    <DocumentCell
                      sourceUrl={hit.sourceUrl}
                      documentId={hit.documentId}
                    />
                  </td>
                  <td className="py-3 pl-4 last:pr-1">
                    <ChunkTextCell text={hit.chunkText} />
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
      </table>
    </div>
  );
};

export default ComparisonTable;
