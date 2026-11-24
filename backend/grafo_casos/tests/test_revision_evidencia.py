import unittest

from steward_datos.contratos import FacturaExtraida

from backend.grafo_casos.revision_evidencia import revisar_evidencia


class TestRevisionEvidencia(unittest.TestCase):
    def test_conserva_lecturas_sin_respaldar_sin_declararlas_verificadas(self):
        factura = FacturaExtraida.model_validate({"campos": {
            "folio": {"valor": "F-9", "etiqueta": "Folio"},
            "emisor_rfc": {"valor": "AAA010101AAA", "etiqueta": "emisor_rfc"},
            "subtotal": {"valor": "1,000.00", "etiqueta": "Subtotal"},
            "emisor_nombre": {"valor": "Empresa Ejemplo SA", "etiqueta": "emisor_nombre"},
        }, "texto_completo": "Empresa Ejemplo SA\nRFC AAA010101AAA\nSubtotal"})
        original = factura.model_dump()
        informe = revisar_evidencia(factura)
        self.assertEqual(factura.model_dump(), original)
        for clave in ("folio", "emisor_rfc", "subtotal"):
            campo = informe["campos"][clave]
            self.assertEqual(campo["valor_leido"], original["campos"][clave]["valor"])
            self.assertEqual(campo["estado"], "pendiente_revision")
            self.assertIsNone(campo["valor_filtro_anterior"])
            self.assertTrue(campo["motivos"])
        self.assertTrue(informe["requiere_revision_humana"])
        self.assertFalse(informe["habilitado_para_decision_automatica"])
        nombre = informe["campos"]["emisor_nombre"]
        self.assertEqual(nombre["estado"], "pendiente_revision")
        self.assertEqual(nombre["valor_leido"], "Empresa Ejemplo SA")

    def test_lectura_inventada_y_confusiones_no_reciben_respaldo(self):
        factura = FacturaExtraida.model_validate({"campos": {
            "folio": {"valor": "INVENTADO", "etiqueta": "Folio"},
            "total": {"valor": "100.00", "etiqueta": "Subtotal"},
            "impuestos": {"valor": "10.00", "etiqueta": "Descuento"},
        }, "texto_completo": "Folio REAL\nSubtotal 100.00\nDescuento 10.00"})
        informe = revisar_evidencia(factura)
        for clave in ("folio", "total", "impuestos"):
            self.assertEqual(informe["campos"][clave]["estado"], "pendiente_revision")
        self.assertEqual(informe["campos"]["folio"]["valor_leido"], "INVENTADO")

    def test_coincidencia_no_es_aprobacion_y_nulo_no_demuestra_ausencia(self):
        factura = FacturaExtraida.model_validate({"campos": {
            "folio": {"valor": "F-9", "etiqueta": "Folio"},
            "retenciones": {"valor": None},
        }, "texto_completo": "Folio F-9", "conceptos": [
            {"descripcion": "Servicio", "importe": "999.00"},
        ]})
        informe = revisar_evidencia(factura)
        self.assertEqual(informe["campos"]["folio"]["estado"], "coincidencia_textual")
        for clave in ("retenciones", "fecha"):
            self.assertEqual(informe["campos"][clave]["estado"], "sin_valor_leido")
        self.assertEqual(informe["conceptos_leidos"][0]["importe"], "999.00")
        self.assertFalse(informe["conceptos_verificados"])
        self.assertTrue(informe["requiere_revision_humana"])
