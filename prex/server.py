"""Local HTTP server for the PREx UI.

Serves the pre-built Vite bundle from `prex/_ui_dist/` plus two API endpoints:

    GET /api/brief   ->  artifact_dir/brief.json
    GET /api/graph   ->  artifact_dir/graph.json

Single-user, localhost-only, read-only. We use the stdlib `http.server` because
the routing surface is four routes and we don't want to drag in a framework.
"""
from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Tuple

UI_DIST = Path(__file__).parent / "_ui_dist"


def _make_handler(artifact_dir: Path) -> type[SimpleHTTPRequestHandler]:
    artifact_dir = artifact_dir.resolve()
    ui_dist = UI_DIST.resolve()

    class Handler(SimpleHTTPRequestHandler):
        # SimpleHTTPRequestHandler will resolve self.path against `directory`.
        def __init__(self, *args, **kwargs):  # noqa: D401
            super().__init__(*args, directory=str(ui_dist), **kwargs)

        def log_message(self, format, *args):  # noqa: A002
            # Keep stdout clean; uncomment for debugging.
            pass

        def do_GET(self):  # noqa: N802
            if self.path == "/api/brief":
                return self._serve_json(artifact_dir / "brief.json")
            if self.path == "/api/graph":
                return self._serve_json(artifact_dir / "graph.json")
            # SPA fallback: any path not pointing at a real asset → index.html.
            relative = self.path.lstrip("/").split("?", 1)[0] or "index.html"
            target = (ui_dist / relative).resolve()
            if not (target.is_file() and ui_dist in target.parents):
                self.path = "/index.html"
            return super().do_GET()

        def _serve_json(self, p: Path) -> None:
            if not p.is_file():
                self.send_error(404, f"missing {p.name}")
                return
            data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return Handler


def serve(artifact_dir: Path, port: int = 0) -> Tuple[ThreadingHTTPServer, int]:
    """Bind a ThreadingHTTPServer to 127.0.0.1:port (port=0 picks free port).

    Returns the live server + the bound port. Caller is responsible for
    `serve_forever()` / `shutdown()`.
    """
    if not UI_DIST.exists():
        raise FileNotFoundError(
            f"UI bundle missing at {UI_DIST}. "
            "Run `cd prex-ui && npm run build` to populate it."
        )
    handler_cls = _make_handler(artifact_dir)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    return httpd, httpd.server_address[1]
