import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app


class TestIdentidadChat(unittest.TestCase):
    def test_sin_identidad_no_accede_a_stream_ni_historial(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}), TestClient(app) as cli:
            self.assertEqual(cli.get("/api/chat/conversaciones").status_code, 401)
            self.assertEqual(cli.post("/api/chat/stream", json={"mensaje": "Hola"}).status_code, 401)

    def test_rol_invalido_no_accede(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}), TestClient(app) as cli:
            r = cli.post("/api/chat/stream", json={"mensaje": "Hola"},
                         headers={"X-Usuario": "dev-ana", "X-Rol": "invitado"})
            self.assertEqual(r.status_code, 403)

    def test_cognito_no_acepta_encabezados_dev(self):
        with patch.dict(os.environ, {"AUTH_MODE": "cognito"}), TestClient(app) as cli:
            r = cli.get("/api/chat/conversaciones",
                        headers={"X-Usuario": "dev-ana", "X-Rol": "administrador"})
            self.assertEqual(r.status_code, 401)
