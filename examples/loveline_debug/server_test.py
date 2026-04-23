"""Tests for the Loveline debug HTTP app."""

import json
import threading
from pathlib import Path
from urllib import request

from absl.testing import absltest

from concordia.utils import structured_logging
from examples.loveline_debug import config_io
from examples.loveline_debug import server


class ServerTest(absltest.TestCase):

  def _start_server(self, paths=None):
    app = server.LovelineDebugApp(paths or config_io.StarterPaths())
    httpd = server.ReusableThreadingTCPServer(
        ("127.0.0.1", 0), app.make_handler()
    )
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    return httpd, thread

  def test_debug_server_is_configured_for_quick_port_reuse(self):
    self.assertTrue(server.ReusableThreadingTCPServer.allow_reuse_address)

  def test_default_draft_api_enables_language_model(self):
    httpd, thread = self._start_server()
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
    httpd, thread = self._start_server(paths)
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

  def test_index_serves_cache_busted_app_script_with_no_store_headers(self):
    httpd, thread = self._start_server()
    try:
      port = httpd.server_address[1]
      with request.urlopen(f"http://127.0.0.1:{port}/") as response:  # nosec: local test server
        body = response.read().decode("utf-8")
        cache_control = response.headers.get("Cache-Control")
        pragma = response.headers.get("Pragma")
        expires = response.headers.get("Expires")
    finally:
      httpd.shutdown()
      httpd.server_close()
      thread.join()

    self.assertRegex(body, r'src="/static/app\.js\?v=\d+"')
    self.assertEqual(cache_control, "no-store, max-age=0")
    self.assertEqual(pragma, "no-cache")
    self.assertEqual(expires, "0")

  def test_app_js_serves_no_store_even_with_version_query(self):
    httpd, thread = self._start_server()
    try:
      port = httpd.server_address[1]
      with request.urlopen(
          f"http://127.0.0.1:{port}/static/app.js?v=123"
      ) as response:  # nosec: local test server
        body = response.read().decode("utf-8")
        cache_control = response.headers.get("Cache-Control")
    finally:
      httpd.shutdown()
      httpd.server_close()
      thread.join()

    self.assertIn("async function refreshStatus()", body)
    self.assertEqual(cache_control, "no-store, max-age=0")

  def test_inspect_api_surfaces_active_inputs_from_run_artifacts(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    run_dir = paths.runs_dir / "run_1"
    run_dir.mkdir(parents=True)
    log = structured_logging.SimulationLog()
    log.add_entry(
        step=1,
        timestamp="2026-04-23T00:00:00+00:00",
        entity_name="Alex",
        component_name="entity_action",
        entry_type="entity",
        summary="Alex speaks",
        raw_data={
            "key": "Entity [Alex]",
            "value": {
                "Instructions": {
                    "Key": "Instructions",
                    "Value": "Stay in character as Alex.",
                },
                "Goal": {
                    "Key": "Goal",
                    "Value": "Find a serious match.",
                },
                "__act__": {
                    "Summary": "Action: Alex speaks",
                    "Value": "I am here for something real.",
                },
            },
        },
    )
    log.attach_memories(
        entity_memories={"Alex": ["Alex wants marriage."]},
        game_master_memories=[],
    )
    (run_dir / "structured_log.json").write_text(log.to_json(), encoding="utf-8")
    (run_dir / "config_snapshot.json").write_text(
        json.dumps({
            "contestants": [{
                "name": "Alex",
                "player_specific_context": "Alex ended a long engagement before joining the show.",
                "player_specific_memories": ["Alex wants marriage."],
            }],
            "scene_types": {
                "pod_date": {
                    "rounds": 2,
                    "call_to_action": "Answer Blake with warmth.",
                    "context_override": "Keep the pod energy tentative and intimate.",
                    "memory_filter": "marriage",
                }
            },
            "scenes": [{
                "id": "pod_1",
                "type": "pod_date",
                "participants": ["Alex", "Blake"],
                "premise": {
                    "Alex": ["Alex hears Blake through the wall for the first time."],
                },
            }],
        }),
        encoding="utf-8",
    )
    httpd, thread = self._start_server(paths)
    try:
      port = httpd.server_address[1]
      url = f"http://127.0.0.1:{port}/api/inspect/run_1?step=1&entity=Alex"
      with request.urlopen(url) as response:  # nosec: local test server
        payload = json.loads(response.read().decode("utf-8"))
    finally:
      httpd.shutdown()
      httpd.server_close()
      thread.join()

    selected = payload["selected"]
    self.assertEqual(
        selected["active_inputs"]["instructions"],
        "Stay in character as Alex.",
    )
    self.assertEqual(
        selected["active_inputs"]["call_to_action"],
        "Answer Blake with warmth.",
    )
    self.assertEqual(
        selected["active_inputs"]["scene_premise"],
        ["Alex hears Blake through the wall for the first time."],
    )
    self.assertEqual(
        selected["active_inputs"]["loaded_context"][0]["label"],
        "Player-specific context",
    )
    self.assertEqual(
        selected["active_inputs"]["loaded_memories"][1]["value"],
        ["Alex wants marriage."],
    )


if __name__ == "__main__":
  absltest.main()
