import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

import app


class ServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

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
        self.assertEqual(body.decode(), f"hello from k12 {app.VERSION}\n")

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
