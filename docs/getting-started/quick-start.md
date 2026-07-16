# Quick start

This path uses the mock embedding provider so no model server is required.
Mock vectors are random: the goal is to validate the complete ingestion flow.

## 1. Start Embeddorium

Follow [Installation](installation.md), then open <http://localhost:5173>.

## 2. Create a provider

Open **LLM Providers**, choose **Create new**, and create:

- Provider type: **Mock**
- Model type: **Embedding**
- Name: `mock-embed`
- Vector dimension: keep the displayed default unless you have a reason to
  change it

## 3. Create a dataset

Open **Datasets**, choose **Create new**, and create a **Web** dataset with a
reachable URL. For a bounded first run, use one page and later disable link
following in the pipeline settings.

## 4. Create and launch a pipeline

Open **Pipelines**, choose **Create new**, select the dataset and mock provider,
and create the pipeline. Creation saves a `pending` run; it does not start work.

Select the new pipeline from the left-hand list and click its launch action.
The run becomes `running`.

For a single-page first run, set **Follow child links** off before creating the
pipeline. The default is on.

## 5. Inspect completion

Open **Indexing Runs** and select the run. The page polls a running job every
10 seconds and displays target status, errors or skip reasons, chunk counts, and
embedding progress.

Success means the run is `completed`. Its vectors appear in the Qdrant
dashboard at <http://localhost:6333/dashboard>, and its source artifacts appear
under `tmp/pipeline_run/`.

## 6. Search

Open **Search**, choose **Select pipeline results**, select the completed run,
enter a query, select **Keyword (BM25)** for deterministic behavior with a mock
provider, and submit. Semantic and hybrid modes work mechanically with mock
vectors but their dense ranking is random.
