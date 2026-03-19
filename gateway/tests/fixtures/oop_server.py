from __future__ import annotations

import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--startup-delay", type=float, default=0.0)
    parser.add_argument("--fixed-expected-token", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    port = int(os.environ["CONFLUOX_PLUGIN_PORT"])
    prefix = os.environ["CONFLUOX_PLUGIN_PREFIX"]
    expected_token = (
        os.environ["CONFLUOX_PLUGIN_AUTH_TOKEN"]
        if args.fixed_expected_token is None
        else args.fixed_expected_token
    )
    time.sleep(max(0.0, args.startup_delay))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A003 - stdlib signature
            return

        def _write_json(self, status: int, payload: dict[str, str]) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _token(self) -> str:
            return self.headers.get("X-Confluox-Plugin-Auth", "")

        def do_GET(self) -> None:  # noqa: N802 - stdlib signature
            if self.path == "/__confluox/health":
                if self._token() != expected_token:
                    self._write_json(401, {"error": "unauthorized"})
                    return
                self._write_json(200, {"status": "ok"})
                return

            if self.path == prefix or self.path.startswith(prefix + "/"):
                if self._token() != expected_token:
                    self._write_json(401, {"error": "unauthorized"})
                    return
                self._write_json(200, {"plugin": "api_oop", "path": self.path})
                return

            self._write_json(404, {"error": "not_found"})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
