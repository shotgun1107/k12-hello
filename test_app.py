import tempfile
import sqlite3
import os
import hashlib
from pathlib import Path
from unittest.mock import patch
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

import app


class ServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        database = root / 'hello.sqlite'
        target = json.loads((Path(__file__).parent/'database.json').read_text())['database']['to']
        with sqlite3.connect(database) as db:
            if target == 'v3':
                db.execute('CREATE TABLE visits(id INTEGER PRIMARY KEY, total INTEGER NOT NULL)')
                db.execute('INSERT INTO visits VALUES(1,0)')
            elif target == 'v2':
                db.execute('CREATE TABLE visits(id INTEGER PRIMARY KEY, count INTEGER NOT NULL, total INTEGER NOT NULL)')
                db.execute('INSERT INTO visits VALUES(1,0,0)')
            else:
                db.execute('CREATE TABLE visits(id INTEGER PRIMARY KEY, count INTEGER NOT NULL)')
                db.execute('INSERT INTO visits VALUES(1,0)')
            db.execute('PRAGMA user_version='+target[1:])
        cls.test_value = b'public-test-only-value'
        secret = root / 'hello-greeting'; secret.write_bytes(cls.test_value)
        cls.env = patch.dict(os.environ, {'K12_DB': str(database)}); cls.env.start()
        cls.secret_path = patch.object(app, 'Path', return_value=secret); cls.secret_path.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()
        cls.secret_path.stop(); cls.env.stop(); cls.tmp.cleanup()

    def get(self, path):
        connection = http.client.HTTPConnection(*self.server.server_address)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def test_root(self):
        status, content_type, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertTrue(content_type.startswith("text/plain"))
        self.assertEqual(body.decode(), f"hello from k12 {app.VERSION} visits=1 secret-sha256={hashlib.sha256(self.test_value).hexdigest()[:8]}\n")

    def test_health(self):
        status, _, body = self.get("/healthz")
        self.assertEqual((status, body), (200, b"ok"))

    def test_version(self):
        status, content_type, body = self.get("/version")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json")
        self.assertEqual(json.loads(body), {"version": app.VERSION, "commit": app.COMMIT})

    def test_missing(self):
        self.assertEqual(self.get("/missing")[0], 404)


if __name__ == "__main__":
    unittest.main()
