import { SERVER_URL } from "../components/consts";
import { Provider, ProviderFormValues } from "../components/providers/types";

// REST client for the `/providers` CRUD endpoints. Request/response bodies are
// already camelCase on both sides (see backend `provider_schemas.py`), so the
// Provider union maps straight onto the wire format.

const BASE = `${SERVER_URL}/providers`;
const JSON_HEADERS = { "Content-Type": "application/json" };

// Build the request body (the Provider union without its server-assigned id)
// from the flat form shape, keeping only the fields the provider type uses.
function toPayload(values: ProviderFormValues) {
  const base = {
    name: values.name,
    modelType: values.modelType,
  };
  if (values.providerType === "ollama") {
    return {
      ...base,
      providerType: "ollama" as const,
      port: values.port,
      modelName: values.modelName,
    };
  }
  if (values.providerType === "remote") {
    return {
      ...base,
      providerType: "remote" as const,
      baseUrl: values.baseUrl,
      apiKey: values.apiKey,
      organization: values.organization,
      modelName: values.modelName,
    };
  }
  return { ...base, providerType: "mock" as const };
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchProviders(): Promise<Provider[]> {
  return parse<Provider[]>(await fetch(BASE));
}

export async function createProvider(
  values: ProviderFormValues
): Promise<Provider> {
  return parse<Provider>(
    await fetch(BASE, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(toPayload(values)),
    })
  );
}

export async function updateProvider(
  id: string,
  values: ProviderFormValues
): Promise<Provider> {
  return parse<Provider>(
    await fetch(`${BASE}/${id}`, {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify(toPayload(values)),
    })
  );
}

export async function deleteProvider(id: string): Promise<void> {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Delete failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
}
