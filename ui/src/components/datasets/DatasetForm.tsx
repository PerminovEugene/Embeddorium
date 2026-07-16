import React, { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import Field from "../common/Field";
import TextInput from "../common/TextInput";
import Select, { SelectOption } from "../common/Select";
import MultiPathSelect from "../common/MultiPathSelect";
import { Dataset, DatasetFormValues, DatasetSourceType } from "./types";

interface DatasetFormProps {
  // The dataset to view, or null to create a new one.
  dataset: Dataset | null;
  onSubmit: (values: DatasetFormValues) => void;
  // Delete the selected dataset. Only rendered when viewing an existing one.
  onDelete?: () => void;
  // Disables the submit/delete actions while a request is in flight.
  submitting?: boolean;
}

const SOURCE_TYPE_OPTIONS: SelectOption[] = [
  { value: "web", label: "Web" },
  { value: "local", label: "Local" },
];

const EMPTY_VALUES: DatasetFormValues = {
  name: "",
  sourceType: "web",
  url: "",
  paths: [],
};

const toFormValues = (dataset: Dataset | null): DatasetFormValues => {
  if (!dataset) return EMPTY_VALUES;
  if (dataset.sourceType === "web") {
    return {
      ...EMPTY_VALUES,
      name: dataset.name,
      sourceType: "web",
      url: dataset.url,
    };
  }
  return {
    ...EMPTY_VALUES,
    name: dataset.name,
    sourceType: "local",
    paths: dataset.paths,
  };
};

const DatasetForm: React.FC<DatasetFormProps> = ({
  dataset,
  onSubmit,
  onDelete,
  submitting = false,
}) => {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    control,
    formState: { errors },
  } = useForm<DatasetFormValues>({ defaultValues: toFormValues(dataset) });

  // Re-prefill the form whenever the selected dataset changes (including the
  // switch to "create new", where dataset is null).
  useEffect(() => {
    reset(toFormValues(dataset));
  }, [dataset, reset]);

  const sourceType = watch("sourceType") as DatasetSourceType;
  const isReadOnly = dataset !== null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <fieldset disabled={isReadOnly} className="flex flex-col gap-4">
        <Field label="Name" htmlFor="name" error={errors.name?.message}>
          <TextInput
            id="name"
            placeholder="Dataset name"
            {...register("name", { required: "Name is required" })}
          />
        </Field>

        <Field label="Source type" htmlFor="sourceType">
          <Select
            id="sourceType"
            options={SOURCE_TYPE_OPTIONS}
            {...register("sourceType")}
          />
        </Field>

        {sourceType === "web" && (
          <>
            <Field label="URL" htmlFor="url" error={errors.url?.message}>
              <TextInput
                id="url"
                placeholder="https://example.com"
                {...register("url", { required: "URL is required" })}
              />
            </Field>
          </>
        )}

        {sourceType === "local" && (
          <Field label="Files & folders">
            <Controller
              control={control}
              name="paths"
              render={({ field }) => (
                <MultiPathSelect value={field.value} onChange={field.onChange} />
              )}
            />
          </Field>
        )}
      </fieldset>

      <div className="flex items-center gap-3">
        {!isReadOnly && (
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-md bg-emd-accent text-emd-button-text font-semibold hover:bg-emd-primary transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Create dataset
          </button>
        )}

        {dataset && onDelete && (
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

export default DatasetForm;
