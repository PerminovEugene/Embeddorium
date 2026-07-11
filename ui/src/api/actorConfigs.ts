import { SERVER_URL } from "../components/consts";
import {
  ActorConfig,
  ActorConfigMap,
} from "../components/ingestion-pipelines/types";

// REST client for the `/actor-configs` endpoint. The server discovers every
// actor's strategy plugins (backend/plugins/<actor>/) and returns, per actor,
// the available strategies plus each strategy's declared settings fields; the
// ingestion-pipeline form uses it to render each configurable actor's settings
// form dynamically.
//
// The response is camelCase at every level except each field's `key` value,
// which stays snake_case so it round-trips verbatim into the actor's stored
// settings block.

const BASE = `${SERVER_URL}/actor-configs`;

// Fetch the raw per-actor config list and reduce it to an actor-keyed lookup.
export async function fetchActorConfigs(): Promise<ActorConfigMap> {
  const res = await fetch(BASE);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(
      `Request failed (${res.status})${detail ? `: ${detail}` : ""}`,
    );
  }
  const configs = (await res.json()) as ActorConfig[];
  return Object.fromEntries(configs.map((c) => [c.actor, c.strategies]));
}
