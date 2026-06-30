import React from "react";

interface PageHeaderProps {
  // Small uppercase eyebrow shown above the title.
  eyebrow?: string;
  title: string;
  // Optional supporting copy rendered under the title.
  description?: string;
  // Optional actions (buttons, etc.) aligned to the right on wide screens.
  actions?: React.ReactNode;
}

// Consistent page heading: accent bar + eyebrow, title and optional description.
const PageHeader: React.FC<PageHeaderProps> = ({
  eyebrow,
  title,
  description,
  actions,
}) => (
  <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div className="flex items-start gap-4">
      <span
        aria-hidden
        className="mt-1 h-10 w-1.5 shrink-0 rounded-full bg-gradient-to-b from-emd-primary to-emd-accent"
      />
      <div>
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emd-primary/80">
            {eyebrow}
          </p>
        )}
        <h2 className="font-display text-3xl uppercase tracking-widest text-emd-panel">
          {title}
        </h2>
        {description && (
          <p className="mt-1 max-w-prose text-sm text-emd-panel/60">
            {description}
          </p>
        )}
      </div>
    </div>
    {actions && <div className="shrink-0">{actions}</div>}
  </div>
);

export default PageHeader;
