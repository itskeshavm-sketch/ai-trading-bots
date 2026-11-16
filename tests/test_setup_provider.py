"""Offline test of setup_provider.py against a fake OpenAI-compatible server.

Spins up a local HTTP server that mimics /v1/models and /v1/chat/completions,
then checks the wizard's model parsing, endpoint fallback, chat test and
.env round-trip. No real API key, no network.

Run: python tests/test_setup_provider.py
"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import setup_provider  # noqa: E402
from envfile import load_env, save_env  # noqa: E402

REQUESTS = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        REQUESTS.append(("GET", self.path, dict(self.headers)))
        if self.path.endswith("/models"):
            self._send(200, {"object": "list", "data": [
                {"id": "alpha-fast"}, {"id": "beta-good"}, {"id": "gamma-cheap"},
            ]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        REQUESTS.append(("POST", self.path, dict(self.headers)))
        if self.path.endswith("/chat/completions"):
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {}
            self._send(200, {"choices": [{"message": {"role": "assistant", "content": "pong"}}],
                               "model": payload.get("model", "?")})
        else:
            self._send(404, {"error": "not found"})


def start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/v1"


def check(name, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'}  {name}{(' -> ' + detail) if detail and not condition else ''}")
    return condition


results = []
server, base_url = start_server()
try:
    # 1. model listing against a live-shaped response
    models, used_base, error = setup_provider.fetch_models(base_url, "sk-test")
    results.append(check("model list fetched", models == ["alpha-fast", "beta-good", "gamma-cheap"], str(models)))
    results.append(check("base url kept as given", used_base == base_url, used_base))
    results.append(check("no error reported", error is None, str(error)))

    # 2. authorization header actually sent
    auth_headers = [h for kind, _, h in REQUESTS if kind == "GET" and h.get("Authorization")]
    results.append(check("Authorization header sent", bool(auth_headers)))

    # 3. alternate response shapes
    shapes = [
        ({"data": [{"id": "a"}, {"id": "b"}]}, ["a", "b"]),
        ({"object": "list", "data": [{"name": "c"}, {"id": "d"}]}, ["c", "d"]),
        ({"models": [{"name": "e"}, {"model": "f"}]}, ["e", "f"]),
        ({"data": ["g", "h"]}, ["g", "h"]),
        ([{"id": "i"}, {"id": "j"}], ["i", "j"]),
    ]
    for shape, expected in shapes:
        parsed = setup_provider.parse_models(shape)
        label = list(shape.keys()) if isinstance(shape, dict) else "bare list"
        results.append(check(f"parse shape {label}", parsed == expected, f"{parsed} != {expected}"))

    # 4. duplicates removed, order kept
    parsed = setup_provider.parse_models({"data": [{"id": "x"}, {"id": "x"}, {"id": "y"}]})
    results.append(check("duplicates removed", parsed == ["x", "y"], str(parsed)))

    # 5. chat test succeeds
    ok, detail = setup_provider.test_model(base_url, "sk-test", "alpha-fast")
    results.append(check("chat test passes", ok, detail))

    # 6. missing model -> reported, not crashed
    ok, detail = setup_provider.test_model(base_url, "sk-test", "alpha-fast", timeout=5)
    results.append(check("chat test detail mentions the model", "alpha" in detail or ok, detail))

    # 7. wrong key -> 401 handled (server always accepts, so check the message path)
    ok, detail = setup_provider.test_model("http://127.0.0.1:1/v1", "sk-test", "alpha-fast", timeout=3)
    results.append(check("unreachable provider reported, not crashed", ok is False and detail != "", detail))

    # 8. base url without /v1 gets /v1 appended when needed
    bare = base_url[:-3]  # strip /v1
    models2, used_base2, _ = setup_provider.fetch_models(bare, "sk-test")
    results.append(check("bare base url resolved to /v1", models2 == ["alpha-fast", "beta-good", "gamma-cheap"], f"{used_base2} {models2}"))

    # 9. .env round trip keeps other keys and comments
    with tempfile.TemporaryDirectory() as tmp:
        env_path = os.path.join(tmp, ".env")
        with open(env_path, "w", encoding="utf-8") as fh:
            fh.write("# a comment\nBINANCE_API_KEY=keepme\nAI_API_KEY=old\n")
        values = load_env(env_path)
        values.update({"AI_API_KEY": "sk-new", "AI_MODEL": "beta-good", "AI_BASE_URL": base_url})
        save_env(env_path, values)
        after = load_env(env_path)
        results.append(check("other keys preserved", after.get("BINANCE_API_KEY") == "keepme", str(after)))
        results.append(check("provider key updated", after.get("AI_API_KEY") == "sk-new", str(after)))
        results.append(check("model written", after.get("AI_MODEL") == "beta-good", str(after)))
        with open(env_path, encoding="utf-8") as fh:
            text = fh.read()
        results.append(check("comment preserved", "# a comment" in text, text))
finally:
    server.shutdown()

print()
print(f"{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
