"""Comprueba la redacción con las facturas seleccionadas para la demo."""
from pathlib import Path
import unittest

import yaml

from backend.grafo_casos.flujo_real import redactar_evidencia
from steward_datos.contratos import BuscarPoliticasSalida
from steward_datos.reglas.motor import validar_factura
from steward_datos.sinteticos import anotaciones, contexto_para, factura_desde_anotacion
from steward_datos.validador import preparar_para_redactor


class TestRedactorDemo(unittest.TestCase):
    def test_facturas_y_respaldos(self):
        ruta = Path(__file__).resolve().parents[3] / "datos" / "evaluacion" / "facturas_demo.yaml"
        escenarios = yaml.safe_load(ruta.read_text(encoding="utf-8"))["facturas"]
        referencias = {d["archivo"]: d for d in anotaciones("evaluacion")}
        sin_fragmentos = BuscarPoliticasSalida(fragmentos=[], modelo_embedding="prueba", sin_resultados=True)
        for escenario in escenarios:
            for archivo in (escenario["archivo"], escenario["respaldo"]):
                with self.subTest(archivo=archivo):
                    referencia = referencias[archivo]
                    resultado = validar_factura(archivo, factura_desde_anotacion(referencia), contexto_para(referencia))
                    politicas = preparar_para_redactor(resultado, 1, buscar=lambda _: sin_fragmentos)
                    texto = redactar_evidencia(resultado.model_dump(), politicas.model_dump())
                    self.assertEqual(resultado.resultado_sugerido, escenario["resultado"])
                    self.assertIn(resultado.motivo, texto)
                    self.assertIn("La decisión final corresponde al analista.", texto)
                    self.assertEqual(sorted({h.regla_id for h in resultado.hallazgos}), escenario["reglas"])
                    for h in resultado.hallazgos:
                        self.assertIn(f"{h.regla_id} v{h.regla_version}", texto)
                        self.assertIn(f"{h.politica_id} v{h.politica_version} §{h.politica_seccion}", texto)
                        self.assertIn(h.evidencia, texto)
                        for etiqueta, valor in h.cifras or []:
                            self.assertIn(f"{etiqueta}: {valor}", texto)
