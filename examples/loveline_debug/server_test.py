"""Tests for the Loveline debug HTTP app."""

import json
import socketserver
import threading
from pathlib import Path
from urllib import request

from absl.testing import absltest

from examples.loveline_debug import config_io
from examples.loveline_debug import server


class ServerTest(absltest.TestCase):

  def test_default_draft_api_enables_language_model(self):
    app = server.LovelineDebugApp(config_io.StarterPaths())
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), app.make_handler())
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    try:
      port = httpd.server_address[1]
      url = f"http://127.0.0.1:{port}/api/draft/default"
      with request.urlopen(url) as response:  # nosec: local test server
        payload = json.loads(response.read().decode("utf-8"))
    finally:
      httpd.shutdown()
      httpd.server_close()
      thread.join()

    self.assertFalse(payload["run"]["disable_language_model"])
    self.assertEqual(payload["run"]["api_type"], "ollama")
    self.assertEqual(payload["run"]["model_name"], "qwen3.5:35b-a3b")

  def test_delete_run_api_removes_saved_artifacts(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    run_dir = paths.runs_dir / "run_1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
    app = server.LovelineDebugApp(paths)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), app.make_handler())
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    try:
      port = httpd.server_address[1]
      req = request.Request(
          f"http://127.0.0.1:{port}/api/runs/run_1",
          method="DELETE",
      )
      with request.urlopen(req) as response:  # nosec: local test server
        payload = json.loads(response.read().decode("utf-8"))
    finally:
      httpd.shutdown()
      httpd.server_close()
      thread.join()

    self.assertEqual(payload, {"status": "deleted", "run_id": "run_1"})
    self.assertFalse(run_dir.exists())


if __name__ == "__main__":
  absltest.main()
