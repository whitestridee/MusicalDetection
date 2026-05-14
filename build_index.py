from __future__ import annotations

import argparse

from audio_similarity.index import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an audio similarity index from WAV files.")
    parser.add_argument("--dataset", required=True, help="Path to a folder with WAV files.")
    parser.add_argument("--output", default="index_data", help="Directory to store the built index.")
    args = parser.parse_args()

    index_file, metadata_file = build_index(args.dataset, args.output)
    print(f"Index saved to: {index_file}")
    print(f"Metadata saved to: {metadata_file}")


if __name__ == "__main__":
    main()
