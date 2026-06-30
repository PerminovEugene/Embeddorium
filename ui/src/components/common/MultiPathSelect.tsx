import React, { useCallback, useEffect, useState } from "react";
import {
  listSourceFiles,
  SourceEntry,
  SourceListing,
} from "../../api/sourceFiles";

interface MultiPathSelectProps {
  value: string[];
  onChange: (paths: string[]) => void;
}

// Lets the user browse the server's ingestion source directory and accumulate a
// selection of files and/or folders. Browsing happens server-side (the browser
// can't read real filesystem paths), so every entry carries a path relative to
// the source root — exactly what the backend resolves back to a real file when
// the pipeline launches. The selection is owned by the parent (controlled).
const MultiPathSelect: React.FC<MultiPathSelectProps> = ({ value, onChange }) => {
  // Current directory, relative to the source root ("" = root).
  const [cwd, setCwd] = useState("");
  const [listing, setListing] = useState<SourceListing | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((path: string) => {
    setLoading(true);
    setError(null);
    listSourceFiles(path)
      .then((data) => {
        setListing(data);
        setCwd(data.path);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load("");
  }, [load]);

  const selected = new Set(value);

  const togglePath = (path: string) => {
    if (selected.has(path)) {
      onChange(value.filter((p) => p !== path));
    } else {
      onChange([...value, path]);
    }
  };

  const removePath = (path: string) =>
    onChange(value.filter((p) => p !== path));

  const openDir = (entry: SourceEntry) => load(entry.path);

  // Breadcrumb segments for the current directory, each navigable.
  const crumbs = cwd ? cwd.split("/") : [];
  const crumbPath = (i: number) => crumbs.slice(0, i + 1).join("/");

  return (
    <div className="flex flex-col gap-2">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-1 text-sm text-emd-text flex-wrap">
        <button
          type="button"
          className="hover:underline cursor-pointer"
          onClick={() => load("")}
        >
          sources
        </button>
        {crumbs.map((seg, i) => (
          <React.Fragment key={crumbPath(i)}>
            <span className="text-emd-placeholder">/</span>
            <button
              type="button"
              className="hover:underline cursor-pointer"
              onClick={() => load(crumbPath(i))}
            >
              {seg}
            </button>
          </React.Fragment>
        ))}
      </div>

      {/* Directory listing */}
      <div className="border border-emd-border rounded-md max-h-56 overflow-y-auto">
        {loading && (
          <p className="px-3 py-2 text-sm text-emd-placeholder">Loading…</p>
        )}
        {error && (
          <p className="px-3 py-2 text-sm text-red-500">{error}</p>
        )}
        {!loading && !error && listing && (
          <ul className="flex flex-col">
            {listing.parent !== null && (
              <li>
                <button
                  type="button"
                  className="w-full text-left px-3 py-1.5 text-sm text-emd-text hover:bg-emd-accent/10 cursor-pointer"
                  onClick={() => load(listing.parent ?? "")}
                >
                  📁 ..
                </button>
              </li>
            )}
            {listing.entries.length === 0 && (
              <li className="px-3 py-2 text-sm text-emd-placeholder">
                Empty folder.
              </li>
            )}
            {listing.entries.map((entry) => (
              <li
                key={entry.path}
                className="flex items-center gap-2 px-3 py-1.5 hover:bg-emd-accent/10"
              >
                <input
                  type="checkbox"
                  className="cursor-pointer shrink-0"
                  checked={selected.has(entry.path)}
                  onChange={() => togglePath(entry.path)}
                  aria-label={`Select ${entry.path}`}
                />
                {entry.type === "dir" ? (
                  <button
                    type="button"
                    className="flex-1 text-left text-sm text-emd-text cursor-pointer truncate"
                    onClick={() => openDir(entry)}
                    title={entry.name}
                  >
                    📁 {entry.name}
                  </button>
                ) : (
                  <span
                    className="flex-1 text-sm text-emd-text truncate"
                    title={entry.name}
                  >
                    📄 {entry.name}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Current selection */}
      {value.length > 0 ? (
        <ul className="flex flex-col gap-1 max-h-40 overflow-y-auto">
          {value.map((path) => (
            <li
              key={path}
              className="flex items-center justify-between gap-2 px-2 py-1 rounded bg-white text-emd-text text-sm"
            >
              <span className="truncate" title={path}>
                {path}
              </span>
              <button
                type="button"
                onClick={() => removePath(path)}
                className="text-red-500 hover:text-red-600 cursor-pointer shrink-0"
                aria-label={`Remove ${path}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-emd-placeholder text-sm">
          No files or folders selected.
        </p>
      )}
    </div>
  );
};

export default MultiPathSelect;
