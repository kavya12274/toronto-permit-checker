"""The Toronto Low-Rise Permit Checker in your web browser.

Run it (in Terminal, from this folder):
    python3 app.py
It opens http://localhost:8010 in your browser. Press Control-C in Terminal to stop.

Uses only what comes with Python (plus the "anthropic" library for the AI buttons).
On your computer it runs only for you (localhost). On the public host (render.yaml) it's open to everyone,
with AI limits per visitor and per day (see checker/ai_client.py).
The checking itself is done by the checker/ folder. This file just:
  - serves the web page (web/index.html and web/report.html)
  - hands the form answers to checker.engine.run() and sends back the results
  - (step 14) looks up an address in Toronto Open Data when you ask it to
  - (steps 20-21) sends things to the AI only when you press an AI button: plan reader,
    drawing reader, chatbot, vibes check (see checker/ai_client.py for the $5 limit)
"""

import importlib.util
import json
import os
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from checker.engine import run                       # noqa: E402
from checker.core import load_city, reload_city      # noqa: E402
from checker.fields import FIELDS, SECTIONS          # noqa: E402

PORT = int(os.environ.get("PORT", "8010"))
# On your computer the app only listens to your own computer (127.0.0.1). On the public host,
# render.yaml sets HOST=0.0.0.0 so visitors can reach it.
HOST = os.environ.get("HOST", "127.0.0.1")
PUBLIC = HOST != "127.0.0.1"
WEB = os.path.join(HERE, "web")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml", ".m4a": "audio/mp4", ".mp4": "video/mp4"}


def setup_info():
    """Everything the web page needs to draw the form."""
    data = reload_city("toronto")        # re-read data files, so a re-import shows up without restarting
    project_types = [t["Project type"] for t in data["project_types"]]
    fields = []
    for f in FIELDS:
        f = dict(f)
        if f["key"] == "project_type":
            f["choices"] = project_types
        fields.append(f)
    profiles = {k: v for k, v in data["project_profiles"].items() if not k.startswith("_")}
    return {"fields": fields, "sections": SECTIONS, "profiles": profiles,
            "import_info": data.get("import_info", {}), "city": data.get("city", {}),
            "translations": data.get("translations", {}),
            "glossary": data.get("glossary", {"terms": []}),          # by-law dictionary (hover definitions)
            "stats": data.get("permit_stats"),                         # Toronto permit wait times (open data)
            "lookup_available": importlib.util.find_spec("checker.lookup") is not None}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):          # keep Terminal quiet
        pass

    def send(self, body, content_type="application/json", status=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, default=str)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 32_000_000:              # uploads are limited to 20 MB of files (about 27 MB once encoded)
            raise ValueError("That upload is too big. Keep files under 20 MB in total.")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self.static("index.html")
        if path in ("/report", "/report.html"):
            return self.static("report.html")
        if path == "/api/setup":
            return self.send(setup_info())
        if path == "/api/ai-status":
            from checker.ai_client import status
            return self.send(status(self.visitor()))            # is the AI set up, and how much of the $5 is left
        if path.startswith("/web/"):
            return self.static(path[len("/web/"):])
        if path.startswith("/video/"):         # the demo-video page and your voice recording
            return self.static(path[len("/video/"):], folder=os.path.join(HERE, "video"))
        self.send({"error": "not found"}, status=404)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self.read_json()
            if path == "/api/check":
                return self.send(run(body.get("inputs", {})))
            if path == "/api/whatcan":           # "What can I build?": the rules in reverse
                from checker.whatcan import calculate
                return self.send(calculate(body.get("inputs", {})))
            if path == "/api/compare":           # what-if: 2-3 designs side by side
                from checker.compare import compare
                return self.send(compare(body.get("designs", [])))
            if path.startswith("/api/ai/"):     # the AI features: each runs only when the user presses its button
                return self.ai(path[len("/api/ai/"):], body)
            if path == "/api/lookup":
                from checker import lookup
                return self.send(lookup.lookup_address(body.get("address", "")))
        except Exception as e:             # show the problem instead of crashing
            return self.send({"error": f"{type(e).__name__}: {e}"}, status=500)
        self.send({"error": "not found"}, status=404)

    def visitor(self):
        """Who is asking, for the per-visitor AI limit. On the host, visitors come through Render's front door
        (Cloudflare), which puts the visitor's real address in CF-Connecting-IP (a visitor can't fake it there)."""
        if PUBLIC:
            for h in ("CF-Connecting-IP", "True-Client-IP"):
                if self.headers.get(h):
                    return self.headers[h].strip()
            fwd = self.headers.get("X-Forwarded-For", "")
            if fwd:
                return fwd.split(",")[0].strip()
        return self.client_address[0]

    def ai(self, feature, body):
        from checker.ai_client import AIError, limits_check
        try:
            if feature in ("read-plan", "read-drawings", "chat", "vibes"):
                limits_check(self.visitor())      # public site: per-visitor and per-day limits
            if feature == "read-plan":           # description -> suggested answers to confirm
                from checker.plan_reader import read_plan
                return self.send(read_plan(body.get("description", ""), body.get("current", {})))
            if feature == "read-drawings":       # drawings / PDFs / photos -> answers, checklist, conflicts
                from checker.drawing_reader import read_drawings
                return self.send(read_drawings(body.get("files", []), body.get("answers", {})))
            if feature == "chat":                # "Ask about my project"
                from checker.chat import chat
                return self.send(chat(body.get("messages", []), body.get("answers", {}), body.get("drawings_summary", "")))
            if feature == "vibes":               # vibes check: opinions that quote the guidelines
                from checker.vibes import vibes_check
                return self.send(vibes_check(body.get("answers", {}), body.get("drawings_summary", "")))
        except AIError as e:                     # no key, over budget, no internet...: say so in plain words
            return self.send({"error": str(e), "friendly": True}, status=400)
        return self.send({"error": "not found"}, status=404)

    def static(self, name, folder=WEB):
        full = os.path.normpath(os.path.join(folder, name))
        if not full.startswith(folder) or not os.path.isfile(full):
            return self.send({"error": "not found"}, status=404)
        with open(full, "rb") as f:
            self.send(f.read(), TYPES.get(os.path.splitext(full)[1], "application/octet-stream"))


def main():
    load_city("toronto")                   # fail early if the data files are missing
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Permit checker running at {url}  (press Control-C to stop)", flush=True)
    if "--no-browser" not in sys.argv and not PUBLIC:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
