"""Regression tests for upstream defects fixed during the bug-hunt rounds.

Each test reproduces a concrete failure that shipped in v4.0.0-alpha.1 and
asserts the corrected behavior, so the defect cannot silently return.
"""

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.utils import TempEnv

# Blueprint modules imported from units/ must never drop __pycache__ into the read-only source tree (plugin-model §1).
sys.dont_write_bytecode = True


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


class TestFetchCoverContract(unittest.TestCase):

    def _run(self, url, *flags, cache_home):
        script = Path(__file__).resolve().parents[2] / "shell" / "scripts" / "media" / "fetch_cover.py"
        return subprocess.run(
            [sys.executable, str(script), url, *flags],
            capture_output=True, text=True,
            env={"HOME": str(cache_home), "XDG_CACHE_HOME": str(cache_home),
                 "PATH": os.environ.get("PATH", "/usr/bin:/bin")})

    def test_malformed_urls_still_emit_one_json_document(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            for url in ("http://[::1/x.jpg", "http://host:99999/x.jpg", "http://host:abc/x.jpg",
                        "http://host:-1/x.jpg", "http:///x.jpg", "ftp://host/x.jpg", ""):
                with self.subTest(url=url):
                    result = self._run(url, cache_home=cache)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(json.loads(result.stdout)["path"], "")

    def test_refresh_refetches_and_falls_back_to_the_cache(self):
        import http.server
        import socketserver
        import threading
        payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        url = "http://127.0.0.1:%d/cover.jpg" % server.server_address[1]

        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            first = json.loads(self._run(url, cache_home=cache).stdout)
            self.assertEqual(first["source"], "network")
            self.assertEqual(len(requests), 1)

            cached = json.loads(self._run(url, cache_home=cache).stdout)
            self.assertEqual(cached["source"], "cache")
            self.assertEqual(len(requests), 1)

            refreshed = json.loads(self._run(url, "--refresh", cache_home=cache).stdout)
            self.assertEqual(refreshed["source"], "network")
            self.assertEqual(len(requests), 2)

            server.shutdown()
            server.server_close()
            fallback = json.loads(self._run(url, "--refresh", cache_home=cache).stdout)
            self.assertEqual(fallback["source"], "cache")
            self.assertEqual(fallback["path"], first["path"])
