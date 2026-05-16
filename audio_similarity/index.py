from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .features import extract_features


SUPPORTED_EXTENSIONS = {".wav"}
SUPPORTED_ENGINES = {"numpy", "faiss", "hnsw"}


@dataclass
class TrackRecord:
    track_id: int
    name: str
    path: str


def _row_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    return (matrix / norms).astype(np.float32)


def apply_feature_scaling(
    vectors: np.ndarray,
    feature_mean: np.ndarray,
    feature_std: np.ndarray,
) -> np.ndarray:
    return (vectors - feature_mean) / np.maximum(feature_std, 1e-8)


def iter_audio_files(dataset_dir: str | Path) -> list[Path]:
    root = Path(dataset_dir)
    files = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(files)


def _build_faiss_index(matrix: np.ndarray, output_path: Path) -> Path:
    try:
        import faiss  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError("FAISS is not installed. Install faiss-cpu to use engine='faiss'.") from exc

    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    faiss_path = output_path / "faiss.index"
    faiss.write_index(index, str(faiss_path))
    return faiss_path


def _build_hnsw_index(
    matrix: np.ndarray,
    output_path: Path,
    *,
    hnsw_m: int,
    hnsw_ef_construction: int,
    hnsw_ef_search: int,
) -> Path:
    try:
        import hnswlib  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError("hnswlib is not installed. Install hnswlib to use engine='hnsw'.") from exc

    index = hnswlib.Index(space="cosine", dim=matrix.shape[1])
    index.init_index(max_elements=matrix.shape[0], ef_construction=hnsw_ef_construction, M=hnsw_m)
    index.add_items(matrix, np.arange(matrix.shape[0], dtype=np.int32))
    index.set_ef(max(hnsw_ef_search, 10))
    hnsw_path = output_path / "hnsw.index"
    index.save_index(str(hnsw_path))
    return hnsw_path


def build_index(
    dataset_dir: str | Path,
    output_dir: str | Path,
    *,
    engine: str = "numpy",
    hnsw_m: int = 16,
    hnsw_ef_construction: int = 200,
    hnsw_ef_search: int = 50,
) -> tuple[Path, Path]:
    if engine not in SUPPORTED_ENGINES:
        raise ValueError(f"Unsupported engine '{engine}'. Supported engines: {sorted(SUPPORTED_ENGINES)}")

    dataset_path = Path(dataset_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    files = iter_audio_files(dataset_path)
    if not files:
        raise FileNotFoundError(f"No supported audio files found in {dataset_path}")

    raw_vectors = []
    metadata: list[dict[str, str | int]] = []
    for track_id, file_path in enumerate(files):
        raw_vector = extract_features(file_path)
        raw_vectors.append(raw_vector)
        metadata.append(
            {
                "track_id": track_id,
                "name": file_path.stem,
                "path": str(file_path.resolve()),
            }
        )

    raw_matrix = np.vstack(raw_vectors).astype(np.float32)
    feature_mean = raw_matrix.mean(axis=0).astype(np.float32)
    feature_std = raw_matrix.std(axis=0).astype(np.float32)
    scaled_matrix = apply_feature_scaling(raw_matrix, feature_mean, feature_std)
    matrix = _row_normalize(scaled_matrix)

    index_file = output_path / "embeddings.npy"
    metadata_file = output_path / "metadata.json"
    stats_file = output_path / "feature_stats.npz"
    config_file = output_path / "index_config.json"

    np.save(index_file, matrix)
    np.savez(stats_file, feature_mean=feature_mean, feature_std=feature_std)
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    ann_path: str | None = None
    if engine == "faiss":
        ann_path = str(_build_faiss_index(matrix, output_path).name)
    elif engine == "hnsw":
        ann_path = str(
            _build_hnsw_index(
                matrix,
                output_path,
                hnsw_m=hnsw_m,
                hnsw_ef_construction=hnsw_ef_construction,
                hnsw_ef_search=hnsw_ef_search,
            ).name
        )

    config = {
        "engine": engine,
        "dimension": int(matrix.shape[1]),
        "count": int(matrix.shape[0]),
        "metric": "cosine",
        "ann_path": ann_path,
        "hnsw_m": hnsw_m,
        "hnsw_ef_construction": hnsw_ef_construction,
        "hnsw_ef_search": hnsw_ef_search,
    }
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_file, metadata_file


def load_index(index_dir: str | Path) -> tuple[np.ndarray, list[TrackRecord], np.ndarray, np.ndarray, dict]:
    root = Path(index_dir)
    matrix = np.load(root / "embeddings.npy").astype(np.float32)
    raw_metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    metadata = [TrackRecord(**item) for item in raw_metadata]

    stats_file = root / "feature_stats.npz"
    if stats_file.exists():
        stats = np.load(stats_file)
        feature_mean = stats["feature_mean"].astype(np.float32)
        feature_std = stats["feature_std"].astype(np.float32)
    else:
        feature_mean = np.zeros(matrix.shape[1], dtype=np.float32)
        feature_std = np.ones(matrix.shape[1], dtype=np.float32)

    config_path = root / "index_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = {
            "engine": "numpy",
            "dimension": int(matrix.shape[1]),
            "count": int(matrix.shape[0]),
            "metric": "cosine",
            "ann_path": None,
        }

    return matrix, metadata, feature_mean, feature_std, config
