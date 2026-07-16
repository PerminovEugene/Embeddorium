import { SERVER_URL } from "../components/consts";
import { Dataset, DatasetFormValues } from "../components/datasets/types";

// REST client for the `/datasets` CRUD endpoints. Request/response bodies are
// already camelCase on both sides (see backend `dataset_schemas.py`), so the
// Dataset union maps straight onto the wire format.

const BASE = `${SERVER_URL}/datasets`;
const JSON_HEADERS = { "Content-Type": "application/json" };

// Build the request body (the Dataset union without its server-assigned id)
// from the flat form shape, normalising the web-only fields.
function toPayload(values: DatasetFormValues) {
  return values.sourceType === "web"
    ? {
        name: values.name,
        sourceType: "web" as const,
        url: values.url,
      }
    : {
        name: values.name,
        sourceType: "local" as const,
        paths: values.paths,
      };
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchDatasets(): Promise<Dataset[]> {
  return parse<Dataset[]>(await fetch(BASE));
}

export async function createDataset(
  values: DatasetFormValues
): Promise<Dataset> {
  return parse<Dataset>(
    await fetch(BASE, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(toPayload(values)),
    })
  );
}

export async function updateDataset(
  id: string,
  values: DatasetFormValues
): Promise<Dataset> {
  return parse<Dataset>(
    await fetch(`${BASE}/${id}`, {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify(toPayload(values)),
    })
  );
}

export async function deleteDataset(id: string): Promise<void> {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Delete failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
}
