"""HTTP app for the Loveline stock-Concordia debug UI."""

from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path
from typing import Any
from urllib import parse
import http.server
import socketserver

from examples.loveline_debug import config_io
from examples.loveline_debug import runner


STATIC_DIR = Path(__file__).with_name("static")


class LovelineDebugApp:
  def __init__(self, paths: config_io.StarterPaths):
    self.paths = paths
    self.runs = runner.RunManager(paths)

  def make_handler(self):
    app = self

    class Handler(http.server.BaseHTTPRequestHandler):
      def log_message(self, format: str, *args: Any) -> None:  # pylint: disable=redefined-builtin
        del format, args

      def do_GET(self) -> None:  # pylint: disable=invalid-name
        parsed = parse.urlparse(self.path)
        try:
          if parsed.path == "/":
            self._serve_file(STATIC_DIR / "index.html")
          elif parsed.path.startswith("/static/"):
            self._serve_file(STATIC_DIR / parsed.path.removeprefix("/static/"))
          elif parsed.path == "/api/source":
            self._send_json(config_io.list_source_data(app.paths))
          elif parsed.path == "/api/draft/default":
            self._send_json(config_io.make_default_draft(app.paths))
          elif parsed.path == "/api/draft/selection":
            query = parse.parse_qs(parsed.query)
            ids = query.get("ids", [""])[0].split(",")
            self._send_json(config_io.make_draft_for_selection(ids, app.paths))
          elif parsed.path == "/api/drafts":
            self._send_json(config_io.list_drafts(app.paths))
          elif parsed.path == "/api/draft":
            query = parse.parse_qs(parsed.query)
            self._send_json(config_io.load_draft(query["name"][0], app.paths))
          elif parsed.path == "/api/status":
            self._send_json(app.runs.status())
          elif parsed.path == "/api/runs":
            self._send_json(app.runs.list_runs())
          elif parsed.path.startswith("/artifacts/"):
            self._serve_artifact(parsed.path.removeprefix("/artifacts/"))
          else:
            self.send_error(404)
        except Exception as exc:  # pylint: disable=broad-exception-caught
          self._send_json({"error": str(exc)}, status=500)

      def do_POST(self) -> None:  # pylint: disable=invalid-name
        try:
          if self.path == "/api/draft":
            payload = self._read_json()
            path = config_io.save_draft(
                payload["draft"], payload.get("name"), app.paths
            )
            self._send_json({"status": "ok", "path": str(path)})
          elif self.path == "/api/run":
            payload = self._read_json()
            record = app.runs.start_run(payload["draft"])
            self._send_json(record.to_dict())
          elif self.path.startswith("/api/control/"):
            command = self.path.removeprefix("/api/control/")
            self._send_json(app.runs.control(command))
          else:
            self.send_error(404)
        except Exception as exc:  # pylint: disable=broad-exception-caught
          self._send_json({"error": str(exc)}, status=500)

      def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

      def _send_json(self, payload: Any, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

      def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
          self.send_error(404)
          return
        content_type = mimetypes.guess_type(str(path))[0] or "text/plain"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

      def _serve_artifact(self, relative: str) -> None:
        artifact_path = (app.paths.runs_dir / relative).resolve()
        runs_root = app.paths.runs_dir.resolve()
        if runs_root not in artifact_path.parents and artifact_path != runs_root:
          self.send_error(403)
          return
        self._serve_file(artifact_path)

    return Handler


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--port", type=int, default=8765)
  parser.add_argument("--starter-root", type=Path, default=config_io.STARTER_ROOT)
  args = parser.parse_args()

  app = LovelineDebugApp(config_io.StarterPaths(args.starter_root))
  server = socketserver.ThreadingTCPServer(
      ("127.0.0.1", args.port), app.make_handler()
  )
  server.allow_reuse_address = True
  print(f"Loveline debug UI: http://localhost:{args.port}")
  print(f"Starter data: {args.starter_root}")
  server.serve_forever()


if __name__ == "__main__":
  main()
