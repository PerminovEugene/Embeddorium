// A provider supplies a model. It is backed either by a local Ollama instance,
// a remote OpenAI-compatible endpoint, or a mock used for testing. More
// provider types may be added later.
export type ProviderType = "ollama" | "remote" | "mock";

// What the model is used for. Different model types may be wired into
// different stages of the pipeline (e.g. embedding vs. generation).
export type ModelType = "embedding" | "text" | "long-text" | "reranker";

interface ProviderBase {
  id: string;
  name: string;
  modelType: ModelType;
}

export interface OllamaProvider extends ProviderBase {
  providerType: "ollama";
  // Port the local Ollama server listens on.
  port: number;
  // Name of the model to pull/run, e.g. "nomic-embed-text".
  modelName: string;
}

export interface RemoteProvider extends ProviderBase {
  providerType: "remote";
  // Base URL of the OpenAI-compatible endpoint.
  baseUrl: string;
  // API key used for authentication.
  apiKey: string;
  // Optional organization id (OpenAI-specific).
  organization: string;
  // Name of the remote model, e.g. "text-embedding-3-small".
  modelName: string;
}

export interface MockProvider extends ProviderBase {
  providerType: "mock";
}

export type Provider = OllamaProvider | RemoteProvider | MockProvider;

// A single flat shape backing the form (react-hook-form is happiest with one
// flat object). It is mapped to/from the discriminated Provider union.
export interface ProviderFormValues {
  name: string;
  providerType: ProviderType;
  modelType: ModelType;
  // ollama
  port: number;
  // ollama + remote
  modelName: string;
  // remote
  baseUrl: string;
  apiKey: string;
  organization: string;
}
