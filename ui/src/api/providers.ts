import { SERVER_URL } from "../components/consts";
import {
  Provider,
  ProviderFormValues,
  ProviderTypeConfig,
} from "../components/providers/types";

const BASE = `${SERVER_URL}/providers`;
const JSON_HEADERS = { "Content-Type": "application/json" };

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

export async function fetchProviderConfigs(): Promise<ProviderTypeConfig[]> {
  return parse<ProviderTypeConfig[]>(await fetch(`${BASE}/configs`));
}

export async function createProvider(
  values: ProviderFormValues,
): Promise<Provider> {
  return parse<Provider>(
    await fetch(BASE, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(values),
    }),
  );
}

export async function updateProvider(
  id: string,
  values: ProviderFormValues,
): Promise<Provider> {
  return parse<Provider>(
    await fetch(`${BASE}/${id}`, {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify(values),
    }),
  );
}

export async function deleteProvider(id: string): Promise<void> {
  const res = await fetch(`${BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Delete failed (${res.status})${detail ? `: ${detail}` : ""}`);
  }
}
