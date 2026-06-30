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
  // Follow links found on the page.
  processChildLinks: boolean;
  // Only meaningful when processChildLinks is true.
  processCrossDomainLinks: boolean;
  // How many link levels deep to crawl. Only meaningful when
  // processChildLinks is true.
  depth: number;
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
  processChildLinks: boolean;
  processCrossDomainLinks: boolean;
  depth: number;
  // local
  paths: string[];
}
