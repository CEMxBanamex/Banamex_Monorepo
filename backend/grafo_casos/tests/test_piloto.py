from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.grafo_casos.piloto import main


class TestPiloto(unittest.TestCase):
    def test_sin_interaccion_guarda_pausa_y_selecciona_modelo(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "evidencia"
            estado = {"factura": {"campos": {}}, "explicacion": "Revisión pendiente"}
            with patch.dict("os.environ", {"AUTH_MODE": "dev", "DATABASE_URL": "fixture"}), \
                    patch("sys.argv", ["piloto", "fixture.png", "--caso", "F-9501", "--salida", str(salida),
                                       "--modelo", "qwen3-vl:4b-instruct", "--revisar-lecturas", "--sin-interaccion"]), \
                    patch("backend.grafo_casos.piloto.FlujoCasosReal") as constructor, \
                    patch("builtins.input") as entrada, redirect_stdout(StringIO()):
                constructor.return_value.procesar_caso.return_value = estado
                main()
                import os
                self.assertEqual(os.environ["VISION_MODELO"], "qwen3-vl:4b-instruct")
            self.assertTrue(constructor.call_args.kwargs["revisar_lecturas"])
            entrada.assert_not_called()
            constructor.return_value.reanudar_caso.assert_not_called()
            self.assertTrue((salida / "pausa.json").is_file())

    def test_entrada_agotada_conserva_pausa_sin_cerrar(self):
        for entradas in ([EOFError()], ["aceptado", EOFError()]):
            with self.subTest(entradas=entradas), tempfile.TemporaryDirectory() as tmp:
                salida = Path(tmp) / "evidencia"
                estado = {"factura": {"campos": {}}, "explicacion": "Revisión pendiente",
                          "resultado": {"resultado_sugerido": "humana"}}
                with patch.dict("os.environ", {"AUTH_MODE": "dev", "DATABASE_URL": "fixture"}), \
                        patch("sys.argv", ["piloto", "fixture.png", "--caso", "F-9401", "--salida", str(salida)]), \
                        patch("backend.grafo_casos.piloto.FlujoCasosReal") as constructor, \
                        patch("builtins.input", side_effect=entradas), redirect_stdout(StringIO()) as texto:
                    flujo = constructor.return_value
                    flujo.procesar_caso.return_value = estado
                    main()
                flujo.reanudar_caso.assert_not_called()
                self.assertEqual(json.loads((salida / "pausa.json").read_text(encoding="utf-8")), estado)
                self.assertFalse((salida / "final.json").exists())
                self.assertIn("sin decisión final", texto.getvalue())
