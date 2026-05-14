from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .controllers import SearchController


def create_handler(controller: SearchController) -> type[BaseHTTPRequestHandler]:
    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            controller.handle_get(self)

        def do_POST(self) -> None:  # noqa: N802
            controller.handle_post(self)

        def log_message(self, format: str, *args: object) -> None:
            return

    return RequestHandler


def create_server(host: str, port: int, controller: SearchController) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), create_handler(controller))
