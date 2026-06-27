export const validatePort = (port: string): boolean => {
  if (!port.trim()) return false;
  return !isNaN(parseInt(port));
};

export const validateModelName = (name: string): boolean => {
  if (!name.trim()) return false;
  return name.length > 0;
};

export const substituteVariables = (
  text: string,
  variables: { id: string; input: string }[]
): string => {
  console.log(text, variables);
  if (!text) return text;

  return text.replace(/\{\{(.*?)\}\}/g, (match, variableIndex) => {
    const variable = variables[variableIndex];
    return variable ? variable.input : match;
  });
};
