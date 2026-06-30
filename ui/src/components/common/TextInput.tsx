import React from "react";

const baseClass =
  "w-full px-3 py-2 rounded-md border border-emd-border bg-white text-emd-text placeholder-emd-placeholder focus:outline-none focus:ring-2 focus:ring-emd-primary focus:border-emd-primary transition disabled:bg-emd-accent/10 disabled:text-emd-placeholder disabled:cursor-not-allowed";

// Styled text input. Forwards its ref so react-hook-form's `register` works.
const TextInput = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className = "", ...props }, ref) => (
  <input ref={ref} className={`${baseClass} ${className}`} {...props} />
));

TextInput.displayName = "TextInput";

export default TextInput;
