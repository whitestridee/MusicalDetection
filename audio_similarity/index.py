from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .features import extract_features


SUPPORTED_EXTENSIONS = {".wav"}


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


def build_index(dataset_dir: str | Path, output_dir: str | Path) -> tuple[Path, Path]:
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

    np.save(index_file, matrix)
    np.savez(stats_file, feature_mean=feature_mean, feature_std=feature_std)
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_file, metadata_file


def load_index(index_dir: str | Path) -> tuple[np.ndarray, list[TrackRecord], np.ndarray, np.ndarray]:
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

    return matrix, metadata, feature_mean, feature_std
