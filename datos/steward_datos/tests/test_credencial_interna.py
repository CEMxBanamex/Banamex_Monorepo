
"""Pruebas unitarias de las credenciales internas backend-MCP."""

import os
import unittest
from unittest.mock import patch

import jwt

from steward_datos.contratos import ContextoUsuario
from steward_datos.credencial_interna import (
    AUDIENCIA,
    ALGORITMO,
    DURACION_SEGUNDOS,
    EMISOR,
    CredencialInternaInvalida,
    crear_credencial,
    verificar_credencial,
)


SECRETO_PRUEBAS = "secreto-local-de-pruebas-con-mas-de-32-caracteres"


class TestCredencialInterna(unittest.TestCase):

    def setUp(self):
        self.patch_secreto = patch.dict(
            os.environ,
            {"CLAVE_IDENTIDAD_MCP": SECRETO_PRUEBAS},
        )
        self.patch_secreto.start()
        self.addCleanup(self.patch_secreto.stop)

    def test_crear_y_verificar_credencial_analista(self):
        usuario = ContextoUsuario(
            usuario_id="usuario-123",
            rol="analista",
        )

        token = crear_credencial(usuario)
        resultado = verificar_credencial(token)

        self.assertEqual(resultado.usuario_id, "usuario-123")
        self.assertEqual(resultado.rol, "analista")

    def test_crear_y_verificar_credencial_administrador(self):
        usuario = ContextoUsuario(
            usuario_id="admin-123",
            rol="administrador",
        )

        token = crear_credencial(usuario)
        resultado = verificar_credencial(token)

        self.assertEqual(resultado.usuario_id, "admin-123")
        self.assertEqual(resultado.rol, "administrador")

    def test_credencial_tiene_emisor_audiencia_y_expiracion(self):
        usuario = ContextoUsuario(
            usuario_id="usuario-123",
            rol="analista",
        )

        token = crear_credencial(usuario)
        claims = jwt.decode(
            token,
            SECRETO_PRUEBAS,
            algorithms=[ALGORITMO],
            options={
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )

        self.assertEqual(claims["iss"], EMISOR)
        self.assertEqual(claims["aud"], AUDIENCIA)
        self.assertEqual(
            claims["exp"] - claims["iat"],
            DURACION_SEGUNDOS,
        )

    def test_rechaza_token_modificado(self):
        usuario = ContextoUsuario(
            usuario_id="usuario-123",
            rol="analista",
        )

        token = crear_credencial(usuario)
        token_modificado = token[:-1] + (
            "a" if token[-1] != "a" else "b"
        )

        with self.assertRaises(CredencialInternaInvalida):
            verificar_credencial(token_modificado)

    def test_rechaza_token_firmado_con_otro_secreto(self):
        usuario = ContextoUsuario(
            usuario_id="usuario-123",
            rol="analista",
        )

        token = crear_credencial(usuario)

        with patch.dict(
            os.environ,
            {"CLAVE_IDENTIDAD_MCP": "otro-secreto-diferente-y-suficientemente-largo"},
        ):
            with self.assertRaises(CredencialInternaInvalida):
                verificar_credencial(token)

    def test_rechaza_token_vacio(self):
        with self.assertRaises(CredencialInternaInvalida):
            verificar_credencial("")

    def test_rechaza_secreto_no_configurado(self):
        with patch.dict(os.environ, {"CLAVE_IDENTIDAD_MCP": ""}):
            usuario = ContextoUsuario(
                usuario_id="usuario-123",
                rol="analista",
            )

            with self.assertRaises(CredencialInternaInvalida):
                crear_credencial(usuario)


if __name__ == "__main__":
    unittest.main()
