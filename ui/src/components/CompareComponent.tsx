import VariablesSection from "./VariablesSection";
import InputsSection from "./InputsSection";
import ResultTable from "./ResultTable";
import { sectionStyle } from "../styles/styles";
import ModelSelector from "./ModelSelector";
import SimilaritySelector from "./SimilaritySelector";
import OllamaPortInput from "./llmPort";
import SubmitButton from "./Submit";
import SourceModeSelector from "./SourceModeSelector";
import RunSelector from "./RunSelector";
import { useFormContext } from "./FormContext";

const H2 = ({ children }) => (
  <h2
    style={{
      fontSize: "1.25rem",
      fontWeight: "600",
      marginBottom: "1rem",
    }}
  >
    {children}
  </h2>
);

const CompareComponent = () => {
  const { state } = useFormContext();
  const isDb = state.sourceType === "db";

  return (
    <>
      <div
        style={{
          margin: "0 auto",
          maxWidth: 1200,
        }}
      >
        <section style={sectionStyle} className="bg-emd-panel">
          <H2>Configuration</H2>
          <div className="flex flex-col justify-between">
            <div className="flex flex-row gap-3 mb-5">
              {/* In DB mode the embedding provider/model come from the selected
                  pipeline run, so the Ollama port picker is hidden. */}
              {!isDb && <OllamaPortInput />}
              <SourceModeSelector />
              {isDb ? <RunSelector /> : <SimilaritySelector />}
            </div>
            {/* In DB mode the embedding model comes from the selected run, so
                the manual model picker is hidden. */}
            {!isDb && (
              <div>
                <ModelSelector />
              </div>
            )}
          </div>
        </section>

        <section style={sectionStyle} className="bg-emd-panel">
          <H2>{isDb ? "Queries" : "Sources"}</H2>

          <VariablesSection type="source" />
          <hr style={{ border: "1px solid #e5e7eb", margin: "1.5rem 0" }} />
          <InputsSection type="source" />
        </section>

        {!isDb && (
          <section style={sectionStyle} className="bg-emd-panel">
            <H2>Candidates</H2>

            <VariablesSection type="candidate" />
            <hr style={{ border: "1px solid #e5e7eb", margin: "1.5rem 0" }} />
            <InputsSection type="candidate" />
          </section>
        )}

        <SubmitButton />
      </div>
      <div className="w-full text-center">
        <div className="overflow-x-auto mx-auto text-center,">
          <section style={sectionStyle} className="bg-emd-panel">
            <H2>Matches</H2>
            <ResultTable />
          </section>
        </div>
      </div>
    </>
  );
};

export default CompareComponent;
