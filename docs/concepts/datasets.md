# Datasets

A dataset is a reusable source definition stored in PostgreSQL. It is one of:

```text
WebDataset   { id, name, source_type="web", url, created_at }
LocalDataset { id, name, source_type="local", paths[], created_at }
```

## Web sources

The dataset stores only the seed URL. URL normalization, deduplication, keyword
filtering, child-link scheduling, parsing, and chunking are run settings.

Discovered links are normalized by removing the query and fragment, lowercasing
scheme and host, removing default ports, and trimming a non-root trailing
slash. The built-in validation strategy permits a seed and restricts child
links to the parent document's origin.

## Local sources

The normal UI flow stores paths relative to `SOURCE_ROOT`, which defaults to
`sources`. At launch, directories are searched recursively for `*.xml`; files
are queued individually. The local validation plugin resolves each file to an
absolute path and records a `file://` identity for deduplication.

## Snapshots

Creating a pipeline run copies the dataset model into
`pipeline_runs.dataset`. Actors then use that snapshot. Editing the dataset does
not retroactively change existing runs.

Dataset deletion does not delete runs through a foreign key because runs store
JSON snapshots rather than dataset references.
