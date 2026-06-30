import React from "react";

interface CardProps {
  // Optional heading rendered inside the card with a separating border.
  title?: string;
  children: React.ReactNode;
  className?: string;
  // Padding around the body. Defaults to comfortable; pass "tight" for lists.
  padding?: "comfortable" | "tight";
}

// Elevated card used to group content on resource pages.
const Card: React.FC<CardProps> = ({
  title,
  children,
  className = "",
  padding = "comfortable",
}) => (
  <section className={`emd-panel overflow-hidden ${className}`}>
    {title && (
      <h3 className="border-b border-emd-border/10 px-6 py-4 text-base font-semibold text-emd-text">
        {title}
      </h3>
    )}
    <div className={padding === "tight" ? "p-2" : "p-6"}>{children}</div>
  </section>
);

export default Card;
