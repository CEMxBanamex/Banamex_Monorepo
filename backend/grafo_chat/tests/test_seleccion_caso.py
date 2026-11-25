import unittest

from backend.grafo_chat.flujo import _seleccionar_herramienta


class TestSeleccionCaso(unittest.TestCase):
    def test_rechazo_en_panel_consulta_caso(self):
        nombre, argumentos, aviso = _seleccionar_herramienta(
            "casos", "¿Por qué se rechazó la factura F-1042?", "F-1042",
        )
        self.assertEqual(nombre, "consultar_caso")
        self.assertEqual(argumentos, {"entrada": {"caso_id": "F-1042"}})
        self.assertIsNone(aviso)

    def test_identificador_en_pregunta_general(self):
        nombre, argumentos, _ = _seleccionar_herramienta(
            "casos", "Consulta la factura F-1042", None,
        )
        self.assertEqual(nombre, "consultar_caso")
        self.assertEqual(argumentos["entrada"]["caso_id"], "F-1042")

    def test_no_mezcla_identificadores(self):
        nombre, _, aviso = _seleccionar_herramienta(
            "casos", "Consulta la factura F-1043", "F-1042",
        )
        self.assertIsNone(nombre)
        self.assertIn("no coincide", aviso)

    def test_busqueda_sin_caso_conservada(self):
        nombre, _, _ = _seleccionar_herramienta("casos", "Busca facturas", None)
        self.assertEqual(nombre, "buscar_facturas")
