import { Similarity } from "./consts";

export interface Variable {
  input: string;
  id: string;
}

export interface VariableGroup {
  variables: Variable[];
  id: string;
}

export interface Input {
  text: string;
  id: string;
}

export interface ValidationErrors {
  embeddingModelName?: string;
  ollamaPort?: string;
  source?: string;
  candidates?: string;
}

export interface Model {
  name: string;
  id: string;
}

export interface FormState {
  sourceVariableGroups: VariableGroup[];
  sourceInputs: Input[];

  candidateVariableGroups: VariableGroup[];
  candidateInputs: Input[];

  models: Model[];
}

export interface Match {
  source_id: string;
  candidate_id: string;

  sourceText: string;
  candidateText: string;
  model: string;
  [key in Similarity]?: number;
}
