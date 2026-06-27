import Header from "./components/Header";
import CompareComponent from "./components/CompareComponent";
import { FormProvider } from "./components/FormContext";

function App() {
  return (
    <div
      style={{ minHeight: "100vh" }}
      className="bg-emd-background text-emd-text"
    >
      <Header />
      <main
        style={{
          margin: "0 auto",
          paddingLeft: 10,
          paddingRight: 10,
        }}
      >
        <FormProvider>
          <CompareComponent />
        </FormProvider>
      </main>
    </div>
  );
}

export default App;
