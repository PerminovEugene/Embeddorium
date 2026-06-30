import React from "react";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
}

const baseClass =
  "w-full px-3 py-2 rounded-md border border-emd-border bg-white text-emd-text focus:outline-none focus:ring-2 focus:ring-emd-primary focus:border-emd-primary transition disabled:bg-emd-accent/10 disabled:text-emd-placeholder disabled:cursor-not-allowed";

// Styled <select>. Forwards its ref so react-hook-form's `register` works.
const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ options, className = "", ...props }, ref) => (
    <select ref={ref} className={`${baseClass} ${className}`} {...props}>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  )
);

Select.displayName = "Select";

export default Select;
