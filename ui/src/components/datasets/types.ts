// For now a dataset is sourced either from the web (a URL) or from the local
// filesystem (files/folders). More source types may be added later.
export type DatasetSourceType = "web" | "local";

interface DatasetBase {
  id: string;
  name: string;
}

export interface WebDataset extends DatasetBase {
  sourceType: "web";
  url: string;
  // Crawl scope (follow child links / cross-domain / depth) is configured on
  // the ingestion pipeline's schedule_discovered_links actor, not the dataset.
}

export interface LocalDataset extends DatasetBase {
  sourceType: "local";
  // Selected file/folder paths.
  paths: string[];
}

export type Dataset = WebDataset | LocalDataset;

// A single flat shape backing the form (react-hook-form is happiest with one
// flat object). It is mapped to/from the discriminated Dataset union.
export interface DatasetFormValues {
  name: string;
  sourceType: DatasetSourceType;
  // web
  url: string;
  // local
  paths: string[];
}
