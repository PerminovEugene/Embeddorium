import { SERVER_URL } from "../components/consts";

// Client for the `/source-files` browse endpoint. The server walks the mounted
// ingestion source tree and returns directories + .xml files for one level,
// with paths relative to the source root. The dataset form stores those
// relative paths, which the backend resolves back to real files at launch.

const BASE = `${SERVER_URL}/source-files`;

export interface SourceEntry {
  name: string;
  // Path relative to the source root — stored verbatim in dataset.paths.
  path: string;
  type: "dir" | "file";
}

export interface SourceListing {
  // Current directory relative to the source root ("" at the root).
  path: string;
  // Parent directory relative path, or null when at the root.
  parent: string | null;
  entries: SourceEntry[];
}

export async function listSourceFiles(path = ""): Promise<SourceListing> {
  const res = await fetch(`${BASE}?path=${encodeURIComponent(path)}`);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(
      `Failed to list source files (${res.status})${detail ? `: ${detail}` : ""}`
    );
  }
  return res.json() as Promise<SourceListing>;
}
