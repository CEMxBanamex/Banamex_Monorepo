
"""Pruebas unitarias de autenticación del backend."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from fastapi import HTTPException

from backend.api.autenticacion import resolver_usuario
from steward_datos.contratos import ContextoUsuario


class TestAutenticacion(unittest.TestCase):

    def test_usuario_valido_en_modo_dev(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            usuario = resolver_usuario(
                authorization=None,
                x_usuario="dev-ana",
                x_rol="analista",
            )

        self.assertIsInstance(usuario, ContextoUsuario)
        self.assertEqual(usuario.usuario_id, "dev-ana")
        self.assertEqual(usuario.rol, "analista")

    def test_peticion_sin_encabezados(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            with self.assertRaises(HTTPException) as contexto:
                resolver_usuario(
                    authorization=None,
                    x_usuario=None,
                    x_rol=None,
                )

        self.assertEqual(contexto.exception.status_code, 401)

    def test_rol_invalido_en_modo_dev(self):
        with patch.dict(os.environ, {"AUTH_MODE": "dev"}):
            with self.assertRaises(HTTPException) as contexto:
                resolver_usuario(
                    authorization=None,
                    x_usuario="dev-ana",
                    x_rol="invitado",
                )

        self.assertEqual(contexto.exception.status_code, 403)

    def test_cognito_sin_token(self):
        with patch.dict(
            os.environ,
            {
                "AUTH_MODE": "cognito",
                "AWS_REGION": "us-east-1",
                "COGNITO_USER_POOL_ID": "us-east-1_test",
                "COGNITO_CLIENT_ID": "client-test",
            },
        ):
            with self.assertRaises(HTTPException) as contexto:
                resolver_usuario(
                    authorization=None,
                    x_usuario=None,
                    x_rol=None,
                )

        self.assertEqual(contexto.exception.status_code, 401)

    @patch("backend.api.autenticacion._cliente_jwks")
    @patch("backend.api.autenticacion.jwt.decode")
    def test_token_cognito_valido(self, mock_decode, mock_jwks):
        claims = {
            "sub": "12345678-1234-1234-1234-123456789012",
            "token_use": "id",
            "cognito:groups": ["analista"],
        }

        mock_decode.return_value = claims

        clave = SimpleNamespace(key="clave-publica-falsa")
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = clave

        with patch.dict(
            os.environ,
            {
                "AUTH_MODE": "cognito",
                "AWS_REGION": "us-east-1",
                "COGNITO_USER_POOL_ID": "us-east-1_test",
                "COGNITO_CLIENT_ID": "client-test",
            },
        ):
            usuario = resolver_usuario(
                authorization="Bearer token-falso",
                x_usuario=None,
                x_rol=None,
            )

        self.assertEqual(
            usuario.usuario_id,
            "12345678-1234-1234-1234-123456789012",
        )
        self.assertEqual(usuario.rol, "analista")
        mock_jwks.assert_called_once()
        mock_decode.assert_called_once()

    @patch("backend.api.autenticacion._cliente_jwks")
    @patch("backend.api.autenticacion.jwt.decode")
    def test_token_cognito_invalido(self, mock_decode, mock_jwks):
        clave = SimpleNamespace(key="clave-publica-falsa")
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = clave

        mock_decode.side_effect = jwt.InvalidTokenError("Token inválido")

        with patch.dict(
            os.environ,
            {
                "AUTH_MODE": "cognito",
                "AWS_REGION": "us-east-1",
                "COGNITO_USER_POOL_ID": "us-east-1_test",
                "COGNITO_CLIENT_ID": "client-test",
            },
        ):
            with self.assertRaises(HTTPException) as contexto:
                resolver_usuario(
                    authorization="Bearer token-invalido",
                    x_usuario=None,
                    x_rol=None,
                )

        self.assertEqual(contexto.exception.status_code, 401)

    @patch("backend.api.autenticacion._cliente_jwks")
    @patch("backend.api.autenticacion.jwt.decode")
    def test_token_sin_grupo_autorizado(self, mock_decode, mock_jwks):
        mock_decode.return_value = {
            "sub": "12345678-1234-1234-1234-123456789012",
            "token_use": "id",
            "cognito:groups": ["otro_grupo"],
        }

        clave = SimpleNamespace(key="clave-publica-falsa")
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = clave

        with patch.dict(
            os.environ,
            {
                "AUTH_MODE": "cognito",
                "AWS_REGION": "us-east-1",
                "COGNITO_USER_POOL_ID": "us-east-1_test",
                "COGNITO_CLIENT_ID": "client-test",
            },
        ):
            with self.assertRaises(HTTPException) as contexto:
                resolver_usuario(
                    authorization="Bearer token-falso",
                    x_usuario=None,
                    x_rol=None,
                )

        self.assertEqual(contexto.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
