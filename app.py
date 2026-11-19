"""A small HTTP target for the K12 deployment pipeline."""
import hashlib
from pathlib import Path
import json
import sqlite3
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = os.environ.get("VERSION", "dev")
COMMIT = os.environ.get("COMMIT", "unknown")


def greeting_hash():
    return hashlib.sha256(Path('/run/secrets/hello-greeting').read_bytes()).hexdigest()[:8]

def visit():
    with sqlite3.connect(os.environ.get("K12_DB","/data/hello.sqlite"),timeout=10) as db:
        db.execute("UPDATE visits SET total=total+1 WHERE id=1")
        return db.execute("SELECT total FROM visits WHERE id=1").fetchone()[0]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = f"hello from k12 {VERSION} visits={visit()} secret-sha256={greeting_hash()}\n".encode()
            content_type = "text/plain; charset=utf-8"
        elif self.path == "/healthz":
            with sqlite3.connect("file:"+os.environ.get("K12_DB","/data/hello.sqlite")+"?mode=ro",uri=True) as db:
                if db.execute("PRAGMA user_version").fetchone()[0] not in (3,):
                    self.send_error(503); return
                db.execute("SELECT total FROM visits WHERE id=1").fetchone()
            body = b"ok"
            content_type = "text/plain; charset=utf-8"
        elif self.path == "/version":
            body = json.dumps({"version": VERSION, "commit": COMMIT}).encode()
            content_type = "application/json"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    # shutdown must run outside the thread executing serve_forever.
    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
