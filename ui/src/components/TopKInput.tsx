import { useFormContext } from "./FormContext";
import { inputStyle } from "../styles/styles";

// DB-search mode only: how many results (nearest chunks) to return per query.
const TopKInput = () => {
  const { state, changeTopK } = useFormContext();

  return (
    <div className="flex flex-col" style={{ width: 110 }}>
      <label className="text-sm font-medium text-emd-text mb-1" htmlFor="top-k">
        Top K
      </label>
      <input
        id="top-k"
        type="number"
        min={1}
        step={1}
        style={inputStyle}
        value={state.topK}
        onChange={(e) => changeTopK(e.target.value)}
      />
      <span className="text-xs text-emd-text mt-1">Results per query</span>
    </div>
  );
};

export default TopKInput;
