from __future__ import annotations

import argparse
import json

from audio_similarity.search import search_similar


def main() -> None:
    parser = argparse.ArgumentParser(description="Find similar audio tracks.")
    parser.add_argument("--query", required=True, help="Path to a WAV file used as the query.")
    parser.add_argument("--index", default="index_data", help="Directory with embeddings and metadata.")
    parser.add_argument("--top-k", type=int, default=5, help="How many results to return.")
    parser.add_argument(
        "--engine",
        default="auto",
        choices=["auto", "numpy", "faiss", "hnsw"],
        help="Search backend. 'auto' uses the backend recorded in index_config.json.",
    )
    args = parser.parse_args()

    results = search_similar(args.query, args.index, top_k=args.top_k, engine=args.engine)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
