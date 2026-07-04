import React from "react";
import { useFormContext } from "./FormContext";
import { options, Similarity } from "./consts";

export const metricConfig = {
  [Similarity.COSINE]: { min: 0, max: 1, step: 0.01, positive: true },
  [Similarity.DOT]: { min: 0, max: 1000, step: 1, positive: true },
  [Similarity.EUCLIDEAN]: { min: 0, max: 100, step: 0.1, positive: false },
  [Similarity.MANHATTAN]: { min: 0, max: 1000, step: 1, positive: false },
};

interface ScoreRangeSelectorProps {
  lower: {
    [key in Similarity]: number;
  };
  higher: {
    [key in Similarity]: number;
  };
  onChange: (similarity: Similarity, lower: number, higher: number) => void;
}

const ScoreRangeSelector: React.FC<ScoreRangeSelectorProps> = ({
  lower,
  higher,
  onChange,
}) => {
  const { state } = useFormContext();
  const getLowColor = (similarity: Similarity) => {
    const useGreenForHigherScore = metricConfig[similarity].positive;
    return useGreenForHigherScore ? "bg-red-200" : "bg-green-200";
  };
  const getHighColor = (similarity: Similarity) => {
    const useGreenForHigherScore = metricConfig[similarity].positive;
    return useGreenForHigherScore ? "bg-green-200" : "bg-red-200";
  };

  return (
    <div className="flex flex-col gap-4">
      {state.similarities.map((similarity) => {
        const simOption = options.find((o) => o.id === similarity);

        return (
          <div
            key={similarity}
            className="grid grid-cols-[250px_min-content_min-content] items-center justify-end gap-x-6 gap-y-2"
          >
            <div className="text-md font-semibold text-emd-text">
              {simOption?.label}:
            </div>

            {/* Lower */}
            <div className="flex items-center gap-2">
              {/* <span className="text-sm text-emd-text">Low</span> */}
              <input
                type="number"
                step={metricConfig[similarity].step}
                min={metricConfig[similarity].min}
                max={metricConfig[similarity].max}
                value={lower[similarity]}
                onChange={(e) =>
                  onChange(
                    similarity,
                    parseFloat(e.target.value),
                    higher[similarity]
                  )
                }
                className={`p-1 border border-emd-border rounded-md w-24 text-right ${getLowColor(
                  similarity
                )}`}
              />
            </div>

            {/* Higher */}
            <div className="flex items-center gap-2">
              <input
                type="number"
                step={metricConfig[similarity].step}
                min={metricConfig[similarity].min}
                max={metricConfig[similarity].max}
                value={higher[similarity]}
                onChange={(e) =>
                  onChange(
                    similarity,
                    lower[similarity],
                    parseFloat(e.target.value)
                  )
                }
                className={`p-1 border border-emd-border rounded-md w-24 text-right ${getHighColor(
                  similarity
                )}`}
              />
              {/* <span className="text-sm text-emd-text">High</span> */}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ScoreRangeSelector;
