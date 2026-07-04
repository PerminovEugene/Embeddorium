import VariablesSection from "./VariablesSection";
import InputsSection from "./InputsSection";
import ResultTable from "./ResultTable";
import { sectionStyle } from "../styles/styles";
import SimilaritySelector from "./SimilaritySelector";
import ProviderSelector from "./ProviderSelector";
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
          <H2>{isDb ? "Source" : "Sources"}</H2>

          <div className="flex flex-row gap-3 mb-5">
            {/* Source mode first, then the source of the embedding model: in
                manual mode the provider supplies it; in DB mode the selected
                pipeline run does. */}
            <SourceModeSelector />
            {isDb ? <RunSelector /> : <ProviderSelector />}
          </div>

          {/* In manual mode the source variables + inputs live in this same
              card; in DB mode they move to their own "Queries" card below so the
              layout mirrors the manual Sources/Candidates split. */}
          {!isDb && (
            <>
              <hr style={{ border: "1px solid #e5e7eb", margin: "1.5rem 0" }} />
              <VariablesSection type="source" />
              <hr style={{ border: "1px solid #e5e7eb", margin: "1.5rem 0" }} />
              <InputsSection type="source" />
            </>
          )}
        </section>

        {isDb && (
          <section style={sectionStyle} className="bg-emd-panel">
            <H2>Queries</H2>

            <VariablesSection type="source" />
            <hr style={{ border: "1px solid #e5e7eb", margin: "1.5rem 0" }} />
            <InputsSection type="source" />
          </section>
        )}

        {!isDb && (
          <section style={sectionStyle} className="bg-emd-panel">
            <H2>Candidates</H2>

            <VariablesSection type="candidate" />
            <hr style={{ border: "1px solid #e5e7eb", margin: "1.5rem 0" }} />
            <InputsSection type="candidate" />
          </section>
        )}

        {!isDb && (
          <section style={sectionStyle} className="bg-emd-panel">
            <H2>Metrics</H2>
            <SimilaritySelector />
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
