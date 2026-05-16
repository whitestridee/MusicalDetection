from __future__ import annotations

import argparse

from audio_similarity.index import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an audio similarity index from WAV files.")
    parser.add_argument("--dataset", required=True, help="Path to a folder with WAV files.")
    parser.add_argument("--output", default="index_data", help="Directory to store the built index.")
    parser.add_argument(
        "--engine",
        default="numpy",
        choices=["numpy", "faiss", "hnsw"],
        help="Index backend: exact NumPy search, FAISS, or HNSW.",
    )
    parser.add_argument("--hnsw-m", type=int, default=16, help="HNSW graph degree M.")
    parser.add_argument("--hnsw-ef-construction", type=int, default=200, help="HNSW ef_construction parameter.")
    parser.add_argument("--hnsw-ef-search", type=int, default=50, help="HNSW ef_search parameter.")
    args = parser.parse_args()

    index_file, metadata_file = build_index(
        args.dataset,
        args.output,
        engine=args.engine,
        hnsw_m=args.hnsw_m,
        hnsw_ef_construction=args.hnsw_ef_construction,
        hnsw_ef_search=args.hnsw_ef_search,
    )
    print(f"Index saved to: {index_file}")
    print(f"Metadata saved to: {metadata_file}")


if __name__ == "__main__":
    main()
