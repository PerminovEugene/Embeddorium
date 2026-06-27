export enum Similarity {
  COSINE = "cosine",
  EUCLIDEAN = "euclidean",
  DOT = "dot",
  MANHATTAN = "manhattan",
  EUCLIDEAN_NORM = "euclidean_norm",
  DOT_NORM = "dot_norm",
  MANHATTAN_NORM = "manhattan_norm",
}
export const options = [
  { id: Similarity.COSINE, label: "Cosine similarity" },
  { id: Similarity.EUCLIDEAN, label: "Euclidean distance" },
  { id: Similarity.DOT, label: "Dot product" },
  { id: Similarity.MANHATTAN, label: "Manhattan distance" },
  { id: Similarity.DOT_NORM, label: "Dot product (normalized)" },
  { id: Similarity.EUCLIDEAN_NORM, label: "Euclidean distance (normalized)" },
  { id: Similarity.MANHATTAN_NORM, label: "Manhattan distance (normalized)" },
];
