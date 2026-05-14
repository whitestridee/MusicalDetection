from __future__ import annotations

from pathlib import Path

import numpy as np

from .features import extract_features
from .index import TrackRecord, apply_feature_scaling, load_index


def _normalize_query(vector: np.ndarray, feature_mean: np.ndarray, feature_std: np.ndarray) -> np.ndarray:
    scaled = apply_feature_scaling(vector[np.newaxis, :], feature_mean, feature_std)[0]
    norm = np.linalg.norm(scaled)
    if norm == 0.0:
        return scaled.astype(np.float32)
    return (scaled / norm).astype(np.float32)


def _confidence_from_distribution(score: float, scores: np.ndarray) -> float:
    mean = float(np.mean(scores))
    std = float(np.std(scores))
    if std < 1e-8:
        return 0.5

    z_score = (score - mean) / std
    confidence = 1.0 / (1.0 + np.exp(-z_score))
    return float(max(0.0, min(1.0, confidence)))


def cosine_similarity_search(
    query_vector: np.ndarray,
    embeddings: np.ndarray,
    metadata: list[TrackRecord],
    top_k: int = 5,
) -> list[dict[str, str | float | int]]:
    if embeddings.ndim != 2:
        raise ValueError("Embeddings matrix must be 2-dimensional")

    scores = embeddings @ query_vector
    ranked_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in ranked_indices:
        track = metadata[int(idx)]
        similarity = float(scores[int(idx)])
        confidence = _confidence_from_distribution(similarity, scores)
        results.append(
            {
                "track_id": track.track_id,
                "name": track.name,
                "path": track.path,
                "similarity": round(similarity, 4),
                "confidence": round(confidence, 4),
            }
        )
    return results


def search_similar(query_path: str | Path, index_dir: str | Path, top_k: int = 5) -> list[dict[str, str | float | int]]:
    embeddings, metadata, feature_mean, feature_std = load_index(index_dir)
    raw_query_vector = extract_features(query_path)
    query_vector = _normalize_query(raw_query_vector, feature_mean, feature_std)
    return cosine_similarity_search(query_vector, embeddings, metadata, top_k=top_k)
