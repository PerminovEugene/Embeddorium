import React, { useEffect, useMemo, useState } from "react";
import Field from "../common/Field";
import TextInput from "../common/TextInput";
import Select from "../common/Select";
import Checkbox from "../common/Checkbox";
import MultiSelectDropdown from "../common/MultiSelectDropdown";
import { Provider } from "../providers/types";
import { Dataset, DatasetSourceType } from "../datasets/types";
import {
  ActorDef,
  DEFAULT_CHUNKER,
  SettingField,
  chunkDocumentFields,
  chunkerRestrictions,
  embedChunksFields,
  isPluginActor,
  pluginActorFields,
  providerOptions,
  resolveActorChain,
} from "./actors";
import {
  ActorConfigMap,
  ActorSettings,
  IngestionPipeline,
  IngestionPipelineFormValues,
  SettingValue,
} from "./types";

interface IngestionPipelineFormProps {
  // The pipeline to edit, or null to create a new one.
  pipeline: IngestionPipeline | null;
  // Available providers/datasets to choose from.
  providers: Provider[];
  datasets: Dataset[];
  // Per-actor strategy configs discovered from the backend (GET
  // /actor-configs); feed every plugin-backed actor's settings fields —
  // including chunk_document's chunker picker and embed_chunks' provider field.
  actorConfigs: ActorConfigMap;
  onSubmit: (values: IngestionPipelineFormValues) => void;
  // Delete the pipeline being edited. Only rendered when editing.
  onDelete?: () => void;
  submitting?: boolean;
  // When true the form is shown read-only — existing pipelines can't be edited.
  disabled?: boolean;
}

const EMPTY_VALUES: IngestionPipelineFormValues = {
  name: "",
  datasetIds: [],
  actorSettings: {},
};

const toFormValues = (
  pipeline: IngestionPipeline | null
): IngestionPipelineFormValues =>
  pipeline
    ? {
        name: pipeline.name,
        datasetIds: [...pipeline.datasetIds],
        actorSettings: structuredClone(pipeline.actorSettings),
      }
    : structuredClone(EMPTY_VALUES);

const IngestionPipelineForm: React.FC<IngestionPipelineFormProps> = ({
  pipeline,
  providers,
  datasets,
  actorConfigs,
  onSubmit,
  onDelete,
  submitting = false,
  disabled = false,
}) => {
  const [values, setValues] = useState<IngestionPipelineFormValues>(
    toFormValues(pipeline)
  );
  const [nameError, setNameError] = useState<string | null>(null);

  // Re-prefill whenever the selection changes (including the switch to "create
  // new", where pipeline is null).
  useEffect(() => {
    setValues(toFormValues(pipeline));
    setNameError(null);
  }, [pipeline]);

  // Default the embed_chunks provider to the first embedding provider once the
  // providers list is available, unless one is already selected (e.g. editing
  // an existing pipeline). Keeps the stored value in sync so it's persisted on
  // submit. Re-runs on selection change so a freshly-created pipeline is
  // pre-filled too.
  useEffect(() => {
    if (disabled) return;
    const opts = providerOptions(providers);
    if (opts.length === 0) return;
    setValues((prev) => {
      if (prev.actorSettings["embed_chunks"]?.["provider"]) return prev;
      return {
        ...prev,
        actorSettings: {
          ...prev.actorSettings,
          embed_chunks: {
            ...prev.actorSettings["embed_chunks"],
            provider: opts[0].value,
          },
        },
      };
    });
  }, [pipeline, providers, disabled]);

  // Source types of the selected datasets — drives both which actors are in
  // the chain and which strategy (web/local) a plugin actor's fields come from.
  const sourceTypes = useMemo<Set<DatasetSourceType>>(() => {
    const types = new Set<DatasetSourceType>();
    for (const id of values.datasetIds) {
      const dataset = datasets.find((d) => d.id === id);
      if (dataset) types.add(dataset.sourceType);
    }
    return types;
  }, [values.datasetIds, datasets]);

  // The actor chain is derived from the source types of the selected datasets.
  const actorChain = useMemo<ActorDef[]>(
    () => resolveActorChain(sourceTypes),
    [sourceTypes]
  );

  // Currently-selected chunker (defaults to the backend default). Drives which
  // dynamic settings fields the chunk_document actor renders.
  const selectedChunker = String(
    values.actorSettings["chunk_document"]?.["chunker"] ?? DEFAULT_CHUNKER
  );

  // Actor settings are discovered at runtime, so replace each actor's static
  // (empty) settings with its resolved fields: chunk_document gets the chunker
  // picker + the selected chunker's fields; every other plugin-backed actor
  // gets its strategy's fields from GET /actor-configs. Non-plugin actors pass
  // through unchanged. Used for both rendering and submit so the persisted
  // payload matches exactly what's shown.
  const resolvedChain = useMemo<ActorDef[]>(
    () =>
      actorChain.map((actor) => {
        if (actor.key === "chunk_document") {
          return {
            ...actor,
            settings: chunkDocumentFields(actorConfigs, selectedChunker),
            note:
              chunkerRestrictions(actorConfigs, selectedChunker) || undefined,
          };
        }
        if (actor.key === "embed_chunks") {
          return { ...actor, settings: embedChunksFields(actorConfigs) };
        }
        if (isPluginActor(actor.key)) {
          return {
            ...actor,
            settings: pluginActorFields(actorConfigs, actor.key, sourceTypes),
          };
        }
        return actor;
      }),
    [actorChain, selectedChunker, actorConfigs, sourceTypes]
  );

  const getSetting = (actorKey: string, field: SettingField): SettingValue =>
    values.actorSettings[actorKey]?.[field.key] ?? field.default;

  const setSetting = (
    actorKey: string,
    settingKey: string,
    value: SettingValue
  ) =>
    setValues((prev) => ({
      ...prev,
      actorSettings: {
        ...prev.actorSettings,
        [actorKey]: { ...prev.actorSettings[actorKey], [settingKey]: value },
      },
    }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.name.trim()) {
      setNameError("Name is required");
      return;
    }
    // Persist only the settings for actors currently in the chain, filling in
    // defaults so the payload is fully resolved. Uses the resolved chain so the
    // chunk_document block carries the selected chunker + its dynamic fields.
    const actorSettings: ActorSettings = {};
    for (const actor of resolvedChain) {
      actorSettings[actor.key] = Object.fromEntries(
        actor.settings.map((f) => [f.key, getSetting(actor.key, f)])
      );
    }
    onSubmit({ ...values, name: values.name.trim(), actorSettings });
  };

  const datasetOptions = datasets.map((d) => ({
    id: d.id,
    label: d.name,
    sublabel: d.sourceType,
  }));

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Field label="Name" htmlFor="name" error={nameError ?? undefined}>
        <TextInput
          id="name"
          placeholder="Pipeline name"
          value={values.name}
          disabled={disabled}
          onChange={(e) => {
            setValues((prev) => ({ ...prev, name: e.target.value }));
            if (nameError) setNameError(null);
          }}
        />
      </Field>

      <Field label="Datasets">
        <MultiSelectDropdown
          options={datasetOptions}
          value={values.datasetIds}
          onChange={(datasetIds) =>
            setValues((prev) => ({ ...prev, datasetIds }))
          }
          placeholder="Select datasets…"
          emptyMessage="No datasets yet — create one first."
          disabled={disabled}
        />
      </Field>

      {/* Actor config — the chain is selected from the datasets' source types. */}
      <div className="flex flex-col gap-3">
        <h4 className="text-emd-text font-semibold text-sm uppercase tracking-wide">
          Pipeline actors
        </h4>
        {resolvedChain.length === 0 ? (
          <p className="text-emd-placeholder text-sm">
            Select at least one dataset to configure its actor chain.
          </p>
        ) : (
          resolvedChain.map((actor) => (
            <ActorSection
              key={actor.key}
              actor={actor}
              providers={providers}
              disabled={disabled}
              getSetting={(field) => getSetting(actor.key, field)}
              setSetting={(field, value) =>
                setSetting(actor.key, field.key, value)
              }
            />
          ))
        )}
      </div>

      {/* Existing pipelines are read-only, so the action row is create-only. */}
      {!disabled && (
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-emd-accent text-emd-button-text font-semibold hover:bg-emd-primary transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {pipeline ? "Save changes" : "Create pipeline"}
          </button>

          {pipeline && onDelete && (
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
      )}
    </form>
  );
};

// A single actor's collapsible config block. Settings are mock for now.
interface ActorSectionProps {
  actor: ActorDef;
  // Available providers — passed through to SettingControl for "provider" fields.
  providers: Provider[];
  // When true the settings are shown read-only.
  disabled?: boolean;
  getSetting: (field: SettingField) => SettingValue;
  setSetting: (field: SettingField, value: SettingValue) => void;
}

const ActorSection: React.FC<ActorSectionProps> = ({
  actor,
  providers,
  disabled = false,
  getSetting,
  setSetting,
}) => {
  // Build a snapshot of current values for all fields so hidden predicates
  // can inspect sibling field values (e.g. hide chunkSize when strategy=section).
  const currentValues: Record<string, SettingValue> = Object.fromEntries(
    actor.settings.map((f) => [f.key, getSetting(f)])
  );

  return (
    <details
      open
      className="rounded-md border border-emd-border bg-white px-4 py-3"
    >
      <summary className="cursor-pointer font-mono text-sm font-semibold text-emd-primary">
        {actor.name}
      </summary>
      <p className="text-xs text-emd-placeholder mt-1 mb-3">{actor.description}</p>
      {actor.note && (
        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mb-3">
          {actor.note}
        </p>
      )}
      <div className="flex flex-col gap-3">
        {actor.settings
          .filter((field) => !field.hidden?.(currentValues))
          .map((field) => (
            <SettingControl
              key={field.key}
              field={field}
              value={getSetting(field)}
              providers={providers}
              disabled={disabled}
              onChange={(value) => setSetting(field, value)}
            />
          ))}
      </div>
    </details>
  );
};

// Renders the right control for a single setting field.
interface SettingControlProps {
  field: SettingField;
  value: SettingValue;
  // Providers list, needed to build options for "provider" type fields.
  providers: Provider[];
  // When true the control is shown read-only.
  disabled?: boolean;
  onChange: (value: SettingValue) => void;
}

const SettingControl: React.FC<SettingControlProps> = ({
  field,
  value,
  providers,
  disabled = false,
  onChange,
}) => {
  const id = `setting-${field.key}`;

  if (field.type === "checkbox") {
    return (
      <div className="flex flex-col gap-1">
        <Checkbox
          label={field.label}
          checked={Boolean(value)}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
        {field.description && (
          <span className="text-xs text-emd-placeholder">
            {field.description}
          </span>
        )}
      </div>
    );
  }

  if (field.type === "provider") {
    // Options are resolved at render time from the live providers list.
    // Only embedding providers are relevant here.
    const opts = providerOptions(providers);
    return (
      <Field label={field.label} htmlFor={id} description={field.description}>
        <Select
          id={id}
          options={
            opts.length > 0
              ? // Lead with an explicit empty placeholder so the default ""
                // value renders as "unselected" instead of silently showing
                // (but not selecting) the first provider.
                [{ value: "", label: "Select an embedding provider…" }, ...opts]
              : [{ value: "", label: "No embedding providers yet — create one first." }]
          }
          value={String(value)}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
        />
      </Field>
    );
  }

  if (field.type === "select") {
    return (
      <Field label={field.label} htmlFor={id} description={field.description}>
        <Select
          id={id}
          options={field.options}
          value={String(value)}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
        />
      </Field>
    );
  }

  if (field.type === "number") {
    return (
      <Field label={field.label} htmlFor={id} description={field.description}>
        <TextInput
          id={id}
          type="number"
          min={field.min}
          value={Number(value)}
          disabled={disabled}
          onChange={(e) => onChange(e.target.valueAsNumber)}
        />
      </Field>
    );
  }

  return (
    <Field label={field.label} htmlFor={id} description={field.description}>
      <TextInput
        id={id}
        placeholder={field.placeholder}
        value={String(value)}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  );
};

export default IngestionPipelineForm;
