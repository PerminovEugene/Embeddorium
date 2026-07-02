import { SERVER_URL } from "../components/consts";
import { ChunkerConfig } from "../components/ingestion-pipelines/types";

// REST client for the `/chunkers` endpoint. The server discovers chunker
// plugins dynamically (backend/plugins/chunkers/) and returns their config
// metadata; the ingestion-pipeline form uses it to render the chunk_document
// actor's chunker picker and per-chunker settings fields.
//
// The response is camelCase at every level except each field's `key` value,
// which stays snake_case so it round-trips verbatim into the stored
// ChunkDocumentSettings.settings.

const BASE = `${SERVER_URL}/chunkers`;

export async function fetchChunkers(): Promise<ChunkerConfig[]> {
  const res = await fetch(BASE);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(
      `Request failed (${res.status})${detail ? `: ${detail}` : ""}`
    );
  }
  return res.json() as Promise<ChunkerConfig[]>;
}
