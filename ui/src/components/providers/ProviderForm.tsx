import React, { useEffect, useMemo, useState } from "react";
import Checkbox from "../common/Checkbox";
import Field from "../common/Field";
import Select, { SelectOption } from "../common/Select";
import TextInput from "../common/TextInput";
import {
  ModelType,
  Provider,
  ProviderConfigField,
  ProviderConfigValue,
  ProviderFormValues,
  ProviderTypeConfig,
} from "./types";

interface ProviderFormProps {
  provider: Provider | null;
  providerConfigs: ProviderTypeConfig[];
  onSubmit: (values: ProviderFormValues) => void;
  onDelete?: () => void;
  submitting?: boolean;
}

const MODEL_TYPE_LABELS: Record<ModelType, string> = {
  embedding: "Embedding",
  text: "Text",
  "long-text": "Long text",
  reranker: "Reranker",
  "cross-encoder": "Cross encoder",
};

const defaultsFor = (config: ProviderTypeConfig): ProviderFormValues => ({
  name: "",
  providerType: config.name,
  modelType: config.supportedModelTypes[0] ?? "embedding",
  config: Object.fromEntries(config.fields.map((field) => [field.key, field.default])),
});

const valuesFor = (
  provider: Provider | null,
  configs: ProviderTypeConfig[],
): ProviderFormValues => {
  if (provider) {
    const providerConfig = configs.find((config) => config.name === provider.providerType);
    return {
      name: provider.name,
      providerType: provider.providerType,
      modelType: provider.modelType,
      config: {
        ...Object.fromEntries(
          (providerConfig?.fields ?? []).map((field) => [field.key, field.default]),
        ),
        ...provider.config,
      },
    };
  }
  return configs[0]
    ? defaultsFor(configs[0])
    : { name: "", providerType: "", modelType: "embedding", config: {} };
};

const ProviderForm: React.FC<ProviderFormProps> = ({
  provider,
  providerConfigs,
  onSubmit,
  onDelete,
  submitting = false,
}) => {
  const [values, setValues] = useState<ProviderFormValues>(() =>
    valuesFor(provider, providerConfigs),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    setValues(valuesFor(provider, providerConfigs));
    setErrors({});
  }, [provider, providerConfigs]);

  const selectedConfig = useMemo(
    () => providerConfigs.find((config) => config.name === values.providerType),
    [providerConfigs, values.providerType],
  );
  const isReadOnly = provider !== null;

  const setConfigValue = (key: string, value: ProviderConfigValue) => {
    setValues((current) => ({
      ...current,
      config: { ...current.config, [key]: value },
    }));
    setErrors((current) => ({ ...current, [key]: "" }));
  };

  const selectProviderType = (providerType: string) => {
    const config = providerConfigs.find((item) => item.name === providerType);
    if (!config) return;
    setValues((current) => ({
      ...defaultsFor(config),
      name: current.name,
    }));
    setErrors({});
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedConfig) return;

    const nextErrors: Record<string, string> = {};
    if (!values.name.trim()) nextErrors.name = "Name is required";
    for (const field of selectedConfig.fields) {
      const value = values.config[field.key];
      if (field.required && (value === null || value === "")) {
        nextErrors[field.key] = `${field.label} is required`;
      }
      if (field.type === "number" && typeof value === "number") {
        if (field.min != null && value < field.min) {
          nextErrors[field.key] = `${field.label} must be at least ${field.min}`;
        }
        if (field.max != null && value > field.max) {
          nextErrors[field.key] = `${field.label} must be at most ${field.max}`;
        }
      }
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    onSubmit({ ...values, name: values.name.trim() });
  };

  if (providerConfigs.length === 0) {
    return <p className="text-emd-placeholder text-sm">Loading provider types…</p>;
  }

  const providerTypeOptions: SelectOption[] = providerConfigs.map((config) => ({
    value: config.name,
    label: `${config.label} · ${config.type}`,
  }));
  const modelTypeOptions: SelectOption[] = (selectedConfig?.supportedModelTypes ?? []).map(
    (modelType) => ({ value: modelType, label: MODEL_TYPE_LABELS[modelType] }),
  );

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <fieldset disabled={isReadOnly} className="flex flex-col gap-4">
        <Field label="Name" htmlFor="name" error={errors.name}>
          <TextInput
            id="name"
            placeholder="Provider name"
            value={values.name}
            onChange={(event) => {
              setValues((current) => ({ ...current, name: event.target.value }));
              setErrors((current) => ({ ...current, name: "" }));
            }}
          />
        </Field>

        <Field label="Provider type" htmlFor="providerType">
          <Select
            id="providerType"
            options={providerTypeOptions}
            value={values.providerType}
            onChange={(event) => selectProviderType(event.target.value)}
          />
        </Field>

        {selectedConfig && (
          <p className="text-xs text-emd-placeholder">{selectedConfig.description}</p>
        )}

        <Field label="Model type" htmlFor="modelType">
          <Select
            id="modelType"
            options={modelTypeOptions}
            value={values.modelType}
            onChange={(event) =>
              setValues((current) => ({
                ...current,
                modelType: event.target.value as ModelType,
              }))
            }
          />
        </Field>

        {selectedConfig && selectedConfig.fields.length > 0 ? (
          <div className="flex flex-col gap-4 pl-6 border-l-2 border-emd-border">
            {selectedConfig.fields.map((field) => (
              <ConfigControl
                key={field.key}
                field={field}
                value={values.config[field.key] ?? field.default}
                error={errors[field.key]}
                onChange={(value) => setConfigValue(field.key, value)}
              />
            ))}
          </div>
        ) : (
          <p className="text-emd-placeholder text-sm">
            This provider needs no additional configuration.
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

interface ConfigControlProps {
  field: ProviderConfigField;
  value: ProviderConfigValue;
  error?: string;
  onChange: (value: ProviderConfigValue) => void;
}

const ConfigControl: React.FC<ConfigControlProps> = ({
  field,
  value,
  error,
  onChange,
}) => {
  const id = `provider-config-${field.key}`;
  if (field.type === "checkbox") {
    return (
      <Checkbox
        label={field.label}
        checked={Boolean(value)}
        onChange={(event) => onChange(event.target.checked)}
      />
    );
  }
  if (field.type === "select") {
    return (
      <Field label={field.label} htmlFor={id} error={error}>
        <Select
          id={id}
          options={field.options ?? []}
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
        />
      </Field>
    );
  }
  return (
    <Field label={field.label} htmlFor={id} error={error}>
      <TextInput
        id={id}
        type={field.type === "number" ? "number" : field.key === "api_key" ? "password" : "text"}
        min={field.min ?? undefined}
        max={field.max ?? undefined}
        placeholder={field.placeholder ?? undefined}
        value={value == null ? "" : String(value)}
        onChange={(event) =>
          onChange(
            field.type === "number"
              ? event.target.value === ""
                ? null
                : event.target.valueAsNumber
              : event.target.value,
          )
        }
      />
    </Field>
  );
};

export default ProviderForm;
