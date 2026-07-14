export type ProviderType = string;

export type ModelType =
  | "embedding"
  | "text"
  | "long-text"
  | "reranker"
  | "cross-encoder";

export type ProviderConfigValue = string | number | boolean | null;

export interface Provider {
  id: string;
  name: string;
  providerType: ProviderType;
  modelType: ModelType;
  config: Record<string, ProviderConfigValue>;
  createdAt?: string | null;
}

export interface ProviderConfigField {
  key: string;
  label: string;
  type: "text" | "number" | "checkbox" | "select";
  default: ProviderConfigValue;
  min?: number | null;
  max?: number | null;
  options?: { value: string; label: string }[] | null;
  placeholder?: string | null;
  required?: boolean;
}

export interface ProviderTypeConfig {
  name: string;
  label: string;
  description: string;
  type: "builtin" | "remote";
  supportedModelTypes: ModelType[];
  fields: ProviderConfigField[];
}

export interface ProviderFormValues {
  name: string;
  providerType: ProviderType;
  modelType: ModelType;
  config: Record<string, ProviderConfigValue>;
}
