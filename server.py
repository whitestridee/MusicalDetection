from __future__ import annotations

import argparse

from mvc_app.app import create_server
from mvc_app.controllers import SearchController
from mvc_app.models import SearchModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple MVC server for audio similarity search.")
    parser.add_argument("--index", default="index_data", help="Directory with embeddings and metadata.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to.")
    args = parser.parse_args()

    model = SearchModel(args.index)
    controller = SearchController(model=model, upload_dir="temp_uploads")
    server = create_server(args.host, args.port, controller)
    print(f"Server started at http://{args.host}:{args.port}")
    print("Open / to use the upload UI or /search?query=C:/path/to/file.wav&top_k=5")
    server.serve_forever()


if __name__ == "__main__":
    main()
