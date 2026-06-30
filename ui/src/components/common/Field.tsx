import React from "react";

interface FieldProps {
  label: string;
  htmlFor?: string;
  error?: string;
  children: React.ReactNode;
}

// Labeled form-control wrapper with an optional validation message.
const Field: React.FC<FieldProps> = ({ label, htmlFor, error, children }) => (
  <div className="flex flex-col gap-1">
    <label
      htmlFor={htmlFor}
      className="text-sm font-medium text-emd-text"
    >
      {label}
    </label>
    {children}
    {error && <span className="text-sm text-red-500">{error}</span>}
  </div>
);

export default Field;
