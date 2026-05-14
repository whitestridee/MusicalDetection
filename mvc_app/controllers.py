from __future__ import annotations

import json
import tempfile
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .models import SearchModel
from .views import render_home_page


class SearchController:
    """Controller layer for HTTP request handling."""

    def __init__(self, model: SearchModel, upload_dir: str | Path = "temp_uploads") -> None:
        self.model = model
        self.upload_dir = Path(upload_dir)

    def handle_get(self, handler) -> None:
        parsed = urlparse(handler.path)
        if parsed.path == "/":
            self._send_html(handler, render_home_page())
            return

        if parsed.path == "/health":
            self._send_json(handler, {"status": "ok"})
            return

        if parsed.path != "/search":
            self._send_json(handler, {"error": "Use /search?query=<path>&top_k=5"}, status=HTTPStatus.NOT_FOUND)
            return

        params = parse_qs(parsed.query)
        query_path = params.get("query", [None])[0]
        top_k = int(params.get("top_k", ["5"])[0])
        if not query_path:
            self._send_json(handler, {"error": "Parameter 'query' is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            results = self.model.find_similar(query_path, top_k=top_k)
        except Exception as exc:
            self._send_json(handler, {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json(handler, {"query": str(Path(query_path).resolve()), "results": results})

    def handle_post(self, handler) -> None:
        if handler.path != "/search-upload":
            self._send_html(handler, render_home_page(error="Неизвестный маршрут"), status=HTTPStatus.NOT_FOUND)
            return

        temp_path: Path | None = None
        try:
            file_bytes, filename, top_k = self._parse_multipart(handler)
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(filename).suffix or ".wav"
            with tempfile.NamedTemporaryFile(dir=self.upload_dir, suffix=suffix, delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_path = Path(temp_file.name)

            results = self.model.find_similar(temp_path, top_k=top_k)
            self._send_html(handler, render_home_page(results=results, query_name=filename))
        except Exception as exc:
            self._send_html(handler, render_home_page(error=str(exc)), status=HTTPStatus.BAD_REQUEST)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _parse_multipart(self, handler) -> tuple[bytes, str | None, int]:
        content_type = handler.headers.get("Content-Type", "")
        content_length = int(handler.headers.get("Content-Length", "0"))
        if "multipart/form-data" not in content_type or content_length <= 0:
            raise ValueError("Нужна форма multipart/form-data с загруженным файлом")

        raw_body = handler.rfile.read(content_length)
        parser = BytesParser(policy=default)
        message = parser.parsebytes(
            b"Content-Type: " + content_type.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw_body
        )

        file_bytes: bytes | None = None
        filename: str | None = None
        top_k = 5
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            if name == "query_file":
                filename = part.get_filename()
                file_bytes = part.get_payload(decode=True)
            elif name == "top_k":
                value = (part.get_payload(decode=True) or b"5").decode("utf-8", errors="ignore").strip()
                if value:
                    top_k = max(1, min(20, int(value)))

        if not filename or file_bytes is None:
            raise ValueError("Файл не был загружен")
        if not filename.lower().endswith(".wav"):
            raise ValueError("Сейчас через UI поддерживаются только файлы .wav")

        return file_bytes, filename, top_k

    @staticmethod
    def _send_json(handler, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    @staticmethod
    def _send_html(handler, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        response = body.encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(response)))
        handler.end_headers()
        handler.wfile.write(response)
