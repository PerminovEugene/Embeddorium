import React from "react";

interface FieldProps {
  label: string;
  htmlFor?: string;
  error?: string;
  // Optional help text rendered under the control, explaining what it does.
  description?: string;
  children: React.ReactNode;
}

// Labeled form-control wrapper with an optional validation message.
const Field: React.FC<FieldProps> = ({
  label,
  htmlFor,
  error,
  description,
  children,
}) => (
  <div className="flex flex-col gap-1">
    <label
      htmlFor={htmlFor}
      className="text-sm font-medium text-emd-text"
    >
      {label}
    </label>
    {children}
    {description && (
      <span className="text-xs text-emd-placeholder">{description}</span>
    )}
    {error && <span className="text-sm text-red-500">{error}</span>}
  </div>
);

export default Field;
