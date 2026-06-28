import React, { createContext, useContext, useState } from "react";
import { Input, VariableGroup, Variable, Model } from "./types";
import { Match, DbMatch, SourceType, PipelineRun } from "./types";
import { Similarity } from "./consts";

export interface Errors {
  sourceVariableGroups: string[];
  sourceInputs: string[];
  candidateVariableGroups: string[];
  candidateInputs: string[];
}

export interface FormState {
  sourceVariableGroups: VariableGroup[];
  sourceInputs: Input[];

  candidateVariableGroups: VariableGroup[];
  candidateInputs: Input[];

  models: Model[];

  similarities: Similarity[];
  ollamaPort: string;

  // Source mode: "manual" compares user inputs against user candidates;
  // "db" searches the collection of the selected pipeline run for each source
  // input (the run also supplies the embedding model used for the query).
  sourceType: SourceType;
  selectedRun: PipelineRun | null;

  matches: Match[];
  dbMatches: DbMatch[];
}

interface FormContextType {
  state: FormState;

  // Variables
  updateVariable: (
    type: "source" | "candidate",
    groupId: string,
    variableId: string,
    input: string
  ) => void;
  addVariable: (type: "source" | "candidate", groupId: string) => void;
  removeVariable: (
    type: "source" | "candidate",
    groupId: string,
    variableId: string
  ) => void;
  addVariableGroup: (type: "source" | "candidate") => void;
  removeVariableGroup: (type: "source" | "candidate", groupId: string) => void;

  // Inputs
  updateInput: (
    type: "source" | "candidate",
    inputId: string,
    text: string
  ) => void;
  addInput: (type: "source" | "candidate") => void;
  removeInput: (type: "source" | "candidate", inputId: string) => void;

  addModel: () => void;
  removeModel: (id: string) => void;
  updateModel: (id: string, value: string) => void;

  checkSimilarity: (similarity: Similarity) => void;
  changeOllamaPort: (value: string) => void;

  setSourceType: (sourceType: SourceType) => void;
  setSelectedRun: (run: PipelineRun | null) => void;

  // Reset
  resetForm: () => void;

  validate: () => string[];
  setMatches: (matches: Match[]) => void;
  setDbMatches: (matches: DbMatch[]) => void;
  saveFormToStorage: () => void;
}

const FormContext = createContext<FormContextType | null>(null);

export const useFormContext = () => {
  const ctx = useContext(FormContext);
  if (!ctx) throw new Error("useFormContext must be used inside FormProvider");
  return ctx;
};

const STORAGE_KEY = "formState";

// UUID-based helpers
const createVariable = (): Variable => ({
  id: crypto.randomUUID(),
  input: "",
});

const createInput = (): Input => ({
  id: crypto.randomUUID(),
  text: "",
});

const createVariableGroup = (): VariableGroup => ({
  id: crypto.randomUUID(),
  variables: [createVariable()],
});

const createModel = (): Model => ({
  id: crypto.randomUUID(),
  name: "",
});

export const FormProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const getDefaultState = (): FormState => ({
    sourceVariableGroups: [],
    sourceInputs: [createInput()],
    candidateVariableGroups: [],
    candidateInputs: [createInput()],
    models: [createModel()],
    similarities: [Similarity.COSINE],
    ollamaPort: "11434",
    sourceType: "manual",
    selectedRun: null,
    matches: [],
    dbMatches: [],
  });

  const getInitialState = (): FormState => {
    const defaults = getDefaultState();
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as Partial<FormState>;
        // Merge over defaults so state persisted before newer fields existed
        // (e.g. dbMatches/sourceType) is still hydrated with valid values.
        return { ...defaults, ...parsed };
      } catch (e) {
        console.error("Failed to parse stored form state", e);
      }
    }
    return defaults;
  };
  const [state, setState] = useState<FormState>(getInitialState());

  // 🔥 Save to localStorage on submit
  const saveFormToStorage = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  };

  const getKey = (
    type: "source" | "candidate",
    kind: "VariableGroups" | "Inputs"
  ) =>
    `${type}${kind.charAt(0).toUpperCase()}${kind.slice(1)}` as keyof FormState;

  // Variable Groups
  const addVariableGroup = (type: "source" | "candidate") => {
    const key = getKey(type, "VariableGroups");
    setState((prev) => ({
      ...prev,
      [key]: [...(prev[key] as VariableGroup[]), createVariableGroup()],
    }));
  };

  const removeVariableGroup = (
    type: "source" | "candidate",
    groupId: string
  ) => {
    const key = getKey(type, "VariableGroups");
    setState((prev) => ({
      ...prev,
      [key]: (prev[key] as VariableGroup[]).filter(
        (group) => group.id !== groupId
      ),
    }));
  };

  const addVariable = (type: "source" | "candidate", groupId: string) => {
    const key = getKey(type, "VariableGroups");
    setState((prev) => ({
      ...prev,
      [key]: (prev[key] as VariableGroup[]).map((group) =>
        group.id === groupId
          ? { ...group, variables: [...group.variables, createVariable()] }
          : group
      ),
    }));
  };

  const removeVariable = (
    type: "source" | "candidate",
    groupId: string,
    variableId: string
  ) => {
    const key = getKey(type, "VariableGroups");
    setState((prev) => ({
      ...prev,
      [key]: (prev[key] as VariableGroup[])
        .map((group) =>
          group.id === groupId
            ? {
                ...group,
                variables: group.variables.filter((v) => v.id !== variableId),
              }
            : group
        )
        .filter((g) => g.variables.length > 0),
    }));
  };

  const updateVariable = (
    type: "source" | "candidate",
    groupId: string,
    variableId: string,
    input: string
  ) => {
    const key = getKey(type, "VariableGroups");
    setState((prev) => ({
      ...prev,
      [key]: (prev[key] as VariableGroup[]).map((group) =>
        group.id === groupId
          ? {
              ...group,
              variables: group.variables.map((v) =>
                v.id === variableId ? { ...v, input } : v
              ),
            }
          : group
      ),
    }));
  };

  const changeOllamaPort = (port: string) => {
    setState((prev) => ({
      ...prev,
      ollamaPort: port,
    }));
  };

  // Inputs
  const addInput = (type: "source" | "candidate") => {
    const key = getKey(type, "Inputs");
    setState((prev) => ({
      ...prev,
      [key]: [...(prev[key] as Input[]), createInput()],
    }));
  };

  const removeInput = (type: "source" | "candidate", inputId: string) => {
    const key = getKey(type, "Inputs");
    setState((prev) => ({
      ...prev,
      [key]: (prev[key] as Input[]).filter((i) => i.id !== inputId),
    }));
  };

  const updateInput = (
    type: "source" | "candidate",
    inputId: string,
    text: string
  ) => {
    const key = getKey(type, "Inputs");
    setState((prev) => ({
      ...prev,
      [key]: (prev[key] as Input[]).map((i) =>
        i.id === inputId ? { ...i, text } : i
      ),
    }));
  };

  // models

  const addModel = () => {
    setState((prev) => ({
      ...prev,
      models: [...prev.models, createModel()],
    }));
  };

  const removeModel = (id: string) => {
    setState((prev) => ({
      ...prev,
      models: prev.models.filter((m) => m.id !== id),
    }));
  };

  const updateModel = (id: string, input: string) => {
    setState((prev) => ({
      ...prev,
      models: prev.models.map((m) => (m.id === id ? { ...m, name: input } : m)),
    }));
  };

  const setMatches = (matches: Match[]) => {
    setState((prev) => ({
      ...prev,
      matches,
    }));
  };

  const setDbMatches = (dbMatches: DbMatch[]) => {
    setState((prev) => ({
      ...prev,
      dbMatches,
    }));
  };

  const setSourceType = (sourceType: SourceType) => {
    setState((prev) => ({
      ...prev,
      sourceType,
    }));
  };

  const setSelectedRun = (selectedRun: PipelineRun | null) => {
    setState((prev) => ({
      ...prev,
      selectedRun,
    }));
  };

  const checkSimilarity = (similarity: Similarity) => {
    setState((prev) => {
      console.log("context prev similarities", prev.similarities);
      const next = {
        ...prev,
        similarities: prev.similarities.includes(similarity)
          ? prev.similarities.filter((s) => s !== similarity)
          : [...prev.similarities, similarity],
      };
      console.log("context next similarities", next.similarities);
      return next;
    });
  };

  const validate = (): string[] => {
    const errors: string[] = [];
    const isDb = state.sourceType === "db";

    state.sourceInputs.forEach((input) => {
      if (input.text.trim() === "")
        errors.push("Source inputs should not be empty");
    });
    if (state.ollamaPort.trim() === "")
      errors.push("Ollama port should not be empty");

    if (isDb) {
      // The embedding model comes from the selected run, and candidates /
      // similarity metrics are irrelevant: Qdrant ranks the nearest vectors
      // with the distance fixed at collection-creation time.
      if (!state.selectedRun)
        errors.push("Please select a pipeline run to search");
    } else {
      if (state.models.length === 0)
        errors.push("Please add name for at least one model");
      state.models.forEach((model) => {
        if (model.name.trim() === "")
          errors.push("Model name should not be empty");
      });
      state.candidateInputs.forEach((input) => {
        if (input.text.trim() === "")
          errors.push("Candidate inputs should not be empty");
      });
      if (state.similarities.length === 0)
        errors.push("Please select at least one similarity metric");
    }

    return errors;
  };

  // Reset all
  const resetForm = () => {
    localStorage.removeItem(STORAGE_KEY);
    setState(getDefaultState());
  };

  return (
    <FormContext.Provider
      value={{
        state,
        updateVariable,
        addVariable,
        removeVariable,
        addVariableGroup,
        removeVariableGroup,
        updateInput,
        addInput,
        removeInput,
        resetForm,

        addModel,
        removeModel,
        updateModel,

        checkSimilarity,
        changeOllamaPort,

        setSourceType,
        setSelectedRun,

        validate,
        setMatches,
        setDbMatches,
        saveFormToStorage,
      }}
    >
      {children}
    </FormContext.Provider>
  );
};
