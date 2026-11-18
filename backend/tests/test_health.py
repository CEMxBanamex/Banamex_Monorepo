import unittest

from fastapi.testclient import TestClient

from backend.api.main import app


class TestHealth(unittest.TestCase):
    def test_health_responde_200(self):
        respuesta = TestClient(app).get("/api/health")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"status": "ok"})
