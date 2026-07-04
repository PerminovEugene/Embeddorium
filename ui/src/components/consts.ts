export const SERVER_URL =
  import.meta.env.VITE_SERVER_URL ?? "http://localhost:8000";

export enum Similarity {
  COSINE = "cosine",
  EUCLIDEAN = "euclidean",
  DOT = "dot",
  MANHATTAN = "manhattan",
}
export const options = [
  { id: Similarity.COSINE, label: "Cosine similarity" },
  { id: Similarity.EUCLIDEAN, label: "Euclidean distance" },
  { id: Similarity.DOT, label: "Dot product" },
  { id: Similarity.MANHATTAN, label: "Manhattan distance" },
];
