import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import ProvidersPage from "./pages/ProvidersPage";
import DatasetsPage from "./pages/DatasetsPage";
import IngestionPipelinesPage from "./pages/IngestionPipelinesPage";
import PipelineRunsPage from "./pages/PipelineRunsPage";
import SearchComparisonPage from "./pages/SearchComparisonPage";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="providers" element={<ProvidersPage />} />
        <Route path="datasets" element={<DatasetsPage />} />
        <Route
          path="ingestion-pipelines"
          element={<IngestionPipelinesPage />}
        />
        <Route path="pipeline-runs" element={<PipelineRunsPage />} />
        <Route path="search-comparison" element={<SearchComparisonPage />} />
      </Route>
    </Routes>
  );
}

export default App;
