"""Tests for the Loveline debug HTTP app."""

import json
import socketserver
import threading
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


if __name__ == "__main__":
  absltest.main()
