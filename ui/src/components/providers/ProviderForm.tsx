import React, { useEffect } from "react";
import { useForm } from "react-hook-form";
import Field from "../common/Field";
import TextInput from "../common/TextInput";
import Select, { SelectOption } from "../common/Select";
import { Provider, ProviderFormValues, ProviderType } from "./types";

interface ProviderFormProps {
  // The provider to view, or null to create a new one.
  provider: Provider | null;
  onSubmit: (values: ProviderFormValues) => void;
  // Delete the selected provider. Only rendered when viewing an existing one.
  onDelete?: () => void;
  // Disables the submit/delete actions while a request is in flight.
  submitting?: boolean;
}

const PROVIDER_TYPE_OPTIONS: SelectOption[] = [
  { value: "ollama", label: "Local Ollama" },
  { value: "remote", label: "Remote" },
  { value: "mock", label: "Mock" },
];

const MODEL_TYPE_OPTIONS: SelectOption[] = [
  { value: "embedding", label: "Embedding" },
  { value: "text", label: "Text" },
  { value: "long-text", label: "Long-text transformer" },
  { value: "reranker", label: "Reranker" },
];

const EMPTY_VALUES: ProviderFormValues = {
  name: "",
  providerType: "ollama",
  modelType: "embedding",
  port: 11434,
  modelName: "",
  baseUrl: "https://api.openai.com/v1",
  apiKey: "",
  organization: "",
};

const toFormValues = (provider: Provider | null): ProviderFormValues => {
  if (!provider) return EMPTY_VALUES;
  const base = {
    ...EMPTY_VALUES,
    name: provider.name,
    providerType: provider.providerType,
    modelType: provider.modelType,
  };
  if (provider.providerType === "ollama") {
    return { ...base, port: provider.port, modelName: provider.modelName };
  }
  if (provider.providerType === "remote") {
    return {
      ...base,
      baseUrl: provider.baseUrl,
      apiKey: provider.apiKey,
      organization: provider.organization,
      modelName: provider.modelName,
    };
  }
  return base;
};

const ProviderForm: React.FC<ProviderFormProps> = ({
  provider,
  onSubmit,
  onDelete,
  submitting = false,
}) => {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<ProviderFormValues>({ defaultValues: toFormValues(provider) });

  // Re-prefill the form whenever the selected provider changes (including the
  // switch to "create new", where provider is null).
  useEffect(() => {
    reset(toFormValues(provider));
  }, [provider, reset]);

  const providerType = watch("providerType") as ProviderType;
  const isReadOnly = provider !== null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <fieldset disabled={isReadOnly} className="flex flex-col gap-4">
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <TextInput
            id="name"
            placeholder="Provider name"
            {...register("name", { required: "Name is required" })}
          />
        </Field>

        <Field label="Provider type" htmlFor="providerType">
          <Select
            id="providerType"
            options={PROVIDER_TYPE_OPTIONS}
            {...register("providerType")}
          />
        </Field>

        <Field label="Model type" htmlFor="modelType">
          <Select
            id="modelType"
            options={MODEL_TYPE_OPTIONS}
            {...register("modelType")}
          />
        </Field>

        {providerType === "ollama" && (
          <div className="flex flex-col gap-4 pl-6 border-l-2 border-emd-border">
            <Field label="Port" htmlFor="port" error={errors.port?.message}>
              <TextInput
                id="port"
                type="number"
                min={1}
                placeholder="11434"
                {...register("port", {
                  valueAsNumber: true,
                  min: { value: 1, message: "Port must be at least 1" },
                  max: { value: 65535, message: "Port must be at most 65535" },
                })}
              />
            </Field>

            <Field
              label="Model name"
              htmlFor="modelName"
              error={errors.modelName?.message}
            >
              <TextInput
                id="modelName"
                placeholder="nomic-embed-text"
                {...register("modelName", {
                  required: "Model name is required",
                })}
              />
            </Field>
          </div>
        )}

        {providerType === "remote" && (
          <div className="flex flex-col gap-4 pl-6 border-l-2 border-emd-border">
            <Field
              label="Base URL"
              htmlFor="baseUrl"
              error={errors.baseUrl?.message}
            >
              <TextInput
                id="baseUrl"
                placeholder="https://api.openai.com/v1"
                {...register("baseUrl", { required: "Base URL is required" })}
              />
            </Field>

            <Field
              label="API key"
              htmlFor="apiKey"
              error={errors.apiKey?.message}
            >
              <TextInput
                id="apiKey"
                type="password"
                placeholder="sk-…"
                {...register("apiKey", { required: "API key is required" })}
              />
            </Field>

            <Field label="Organization (optional)" htmlFor="organization">
              <TextInput
                id="organization"
                placeholder="org-…"
                {...register("organization")}
              />
            </Field>

            <Field
              label="Model name"
              htmlFor="modelName"
              error={errors.modelName?.message}
            >
              <TextInput
                id="modelName"
                placeholder="text-embedding-3-small"
                {...register("modelName", {
                  required: "Model name is required",
                })}
              />
            </Field>
          </div>
        )}

        {providerType === "mock" && (
          <p className="text-emd-placeholder text-sm">
            The mock provider needs no configuration.
          </p>
        )}
      </fieldset>

      <div className="flex items-center gap-3">
        {!isReadOnly && (
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-emd-accent text-emd-button-text font-semibold hover:bg-emd-primary transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Create provider
          </button>
        )}

        {provider && onDelete && (
          <button
            type="button"
            onClick={onDelete}
            disabled={submitting}
            className="px-4 py-2 rounded-md border border-red-500 text-red-600 font-semibold hover:bg-red-500 hover:text-white transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Delete
          </button>
        )}
      </div>
    </form>
  );
};

export default ProviderForm;
