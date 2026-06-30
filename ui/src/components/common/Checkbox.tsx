import React from "react";

interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: string;
}

// Styled checkbox with an inline label. Forwards its ref so react-hook-form's
// `register` works.
const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, className = "", ...props }, ref) => (
    <label className="flex items-center gap-2 text-sm text-emd-text cursor-pointer">
      <input
        type="checkbox"
        ref={ref}
        className={`accent-emd-primary w-4 h-4 ${className}`}
        {...props}
      />
      <span>{label}</span>
    </label>
  )
);

Checkbox.displayName = "Checkbox";

export default Checkbox;
