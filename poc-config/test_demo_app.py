"""Offline smoke test of the Python application embedded in guide 05b."""

import json
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

guide = (Path(__file__).resolve().parent.parent / "05b-workload-migration-and-testing.md").read_text()
code = guide.split("cat > /home/ssm-user/dce-demo/app.py <<'PY'\n", 1)[1].split("\nPY\n```", 1)[0]

with tempfile.TemporaryDirectory(prefix="dce-app-test-") as temp:
    scope = {"__name__": "demo_test", "__file__": str(Path(temp) / "app.py")}
    exec(compile(code, "05b-app.py", "exec"), scope)
    scope["init_db"]()
    server = scope["ThreadingHTTPServer"](("127.0.0.1", 0), scope["Handler"])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.load(response)

    try:
        assert request("/health")[1]["status"] == "ok"
        assert request("/records")[1]["count"] == 3
        status, _ = request("/records", {"name": "delta-widget", "category": "synthetic"})
        assert status == 201
        scope["init_db"]()  # A restart must not reseed or remove committed rows.
        assert request("/records")[1]["count"] == 4
        for bad in ([], {"name": "x", "category": []}, {"name": ""}):
            try:
                request("/records", bad)
            except urllib.error.HTTPError as error:
                assert error.code == 400
            else:
                raise AssertionError("Invalid input accepted")
        assert request("/records")[1]["count"] == 4
        print("PASS: health, seed, write, persisted state, invalid-input rejection")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
