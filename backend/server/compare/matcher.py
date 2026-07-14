from typing import List, Dict
import numpy as np


# --- Similarity Functions ---
def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def dot_product(vec1: List[float], vec2: List[float]) -> float:
    return np.dot(vec1, vec2)


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    return np.linalg.norm(np.array(vec1) - np.array(vec2))


def manhattan_distance(vec1: List[float], vec2: List[float]) -> float:
    return np.sum(np.abs(np.array(vec1) - np.array(vec2)))


SIMILARITY_METRICS = {
    "cosine": cosine_similarity,
    "dot": dot_product,
    "euclidean": euclidean_distance,
    "manhattan": manhattan_distance,
}


def match_embeddings(
    source: List[List[float]],
    source_ids: List[str],
    candidates: List[List[float]],
    candidate_ids: List[str],
    similarities: List[str],
    sort_by: str = "cosine",
) -> List[Dict]:
    results = []

    for i, src in enumerate(source):
        for j, cand in enumerate(candidates):
            item = {
                "source_id": source_ids[i],
                "candidate_id": candidate_ids[j],
            }
            for sim in similarities:
                func = SIMILARITY_METRICS.get(sim)
                if func:
                    item[sim] = func(src, cand)
            results.append(item)

    return sorted(results, key=lambda x: -x.get(sort_by, 0.0))
