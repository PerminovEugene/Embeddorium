import React from "react";

interface ScrollableListProps<T> {
  items: T[];
  // Stable key for each item.
  getKey: (item: T) => string;
  // How to render the content of a single row.
  renderItem: (item: T) => React.ReactNode;
  // Key of the currently selected item, if any.
  selectedKey?: string | null;
  onSelect?: (item: T) => void;
  // Shown when `items` is empty.
  emptyMessage?: string;
  className?: string;
}

// A generic, vertically scrollable list. It is presentational only: the items
// and selection state are owned by the parent component.
function ScrollableList<T>({
  items,
  getKey,
  renderItem,
  selectedKey,
  onSelect,
  emptyMessage = "No items.",
  className = "",
}: ScrollableListProps<T>) {
  if (items.length === 0) {
    return <p className="text-emd-placeholder text-sm p-3">{emptyMessage}</p>;
  }

  return (
    <ul className={`overflow-y-auto flex flex-col gap-1 ${className}`}>
      {items.map((item) => {
        const key = getKey(item);
        const isSelected = key === selectedKey;
        return (
          <li key={key}>
            <button
              type="button"
              onClick={() => onSelect?.(item)}
              className={`w-full text-left px-3 py-2 rounded-md transition-colors cursor-pointer ${
                isSelected
                  ? "bg-emd-primary text-emd-button-text"
                  : "text-emd-text hover:bg-emd-accent/20"
              }`}
            >
              {renderItem(item)}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default ScrollableList;
