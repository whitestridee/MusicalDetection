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


def _search_numpy(query_vector: np.ndarray, embeddings: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    scores = embeddings @ query_vector
    ranked_indices = np.argsort(scores)[::-1][:top_k]
    return ranked_indices.astype(np.int64), scores


def _search_faiss(query_vector: np.ndarray, index_dir: Path, embeddings: np.ndarray, config: dict, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    try:
        import faiss  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError("FAISS engine requested, but faiss-cpu is not installed.") from exc

    ann_path = config.get("ann_path")
    if not ann_path:
        raise FileNotFoundError("FAISS index file is missing from index_config.json")

    index = faiss.read_index(str(index_dir / ann_path))
    distances, labels = index.search(query_vector[np.newaxis, :], top_k)
    scores = embeddings @ query_vector
    valid_labels = labels[0][labels[0] >= 0]
    return valid_labels.astype(np.int64), scores


def _search_hnsw(query_vector: np.ndarray, index_dir: Path, embeddings: np.ndarray, config: dict, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    try:
        import hnswlib  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError("HNSW engine requested, but hnswlib is not installed.") from exc

    ann_path = config.get("ann_path")
    if not ann_path:
        raise FileNotFoundError("HNSW index file is missing from index_config.json")

    index = hnswlib.Index(space="cosine", dim=int(config["dimension"]))
    index.load_index(str(index_dir / ann_path))
    index.set_ef(max(int(config.get("hnsw_ef_search", 50)), top_k))
    labels, _distances = index.knn_query(query_vector[np.newaxis, :], k=top_k)
    scores = embeddings @ query_vector
    valid_labels = labels[0][labels[0] >= 0]
    return valid_labels.astype(np.int64), scores


def _search_with_engine(
    query_vector: np.ndarray,
    index_dir: Path,
    embeddings: np.ndarray,
    config: dict,
    top_k: int,
    engine: str,
) -> tuple[np.ndarray, np.ndarray, str]:
    selected_engine = config.get("engine", "numpy") if engine == "auto" else engine
    if selected_engine == "numpy":
        ranked_indices, scores = _search_numpy(query_vector, embeddings, top_k)
    elif selected_engine == "faiss":
        ranked_indices, scores = _search_faiss(query_vector, index_dir, embeddings, config, top_k)
    elif selected_engine == "hnsw":
        ranked_indices, scores = _search_hnsw(query_vector, index_dir, embeddings, config, top_k)
    else:
        raise ValueError(f"Unsupported search engine '{selected_engine}'")
    return ranked_indices, scores, selected_engine


def cosine_similarity_search(
    query_vector: np.ndarray,
    index_dir: Path,
    embeddings: np.ndarray,
    metadata: list[TrackRecord],
    config: dict,
    top_k: int = 5,
    engine: str = "auto",
) -> list[dict[str, str | float | int]]:
    if embeddings.ndim != 2:
        raise ValueError("Embeddings matrix must be 2-dimensional")

    ranked_indices, scores, selected_engine = _search_with_engine(
        query_vector,
        index_dir,
        embeddings,
        config,
        top_k,
        engine,
    )

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
                "engine": selected_engine,
            }
        )
    return results


def search_similar(
    query_path: str | Path,
    index_dir: str | Path,
    top_k: int = 5,
    engine: str = "auto",
) -> list[dict[str, str | float | int]]:
    resolved_index_dir = Path(index_dir)
    embeddings, metadata, feature_mean, feature_std, config = load_index(resolved_index_dir)
    raw_query_vector = extract_features(query_path)
    query_vector = _normalize_query(raw_query_vector, feature_mean, feature_std)
    return cosine_similarity_search(
        query_vector,
        resolved_index_dir,
        embeddings,
        metadata,
        config,
        top_k=top_k,
        engine=engine,
    )
