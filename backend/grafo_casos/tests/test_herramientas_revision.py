from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from backend.grafo_casos.herramientas_reales import HerramientasReales
from steward_datos.contratos import ContextoUsuario
from steward_datos.db.models import ACCIONES_BITACORA, EventoBitacora


class TestGuardarRevision(unittest.TestCase):
    def test_guarda_informe_y_resultado_original_en_la_misma_sesion(self):
        sesion = MagicMock()

        @contextmanager
        def abrir():
            yield sesion

        tools = HerramientasReales(ContextoUsuario(usuario_id="dev-ana", rol="analista"))
        factura = {"campos": {"folio": {"valor": "F-8", "etiqueta": "Folio"}}}
        resultado = {"caso_id": "F-9201", "reglas_evaluadas": [], "hallazgos": [],
                     "resultado_sugerido": "humana", "motivo": "Lecturas pendientes"}
        original = {**resultado, "resultado_sugerido": "aceptado"}
        informe = {"version": "prueba", "requiere_revision_humana": True}
        with patch("backend.grafo_casos.herramientas_reales.sesion", abrir), \
                patch.object(tools, "_caso", return_value=SimpleNamespace(estado="procesando")), \
                patch("backend.grafo_casos.herramientas_reales.guardar_extraccion") as extraccion, \
                patch("backend.grafo_casos.herramientas_reales.guardar_resultado") as validacion:
            tools.guardar("F-9201", factura, resultado, "Lectura pendiente", {},
                          revision_evidencia=informe, resultado_reglas=original)
        self.assertIs(extraccion.call_args.args[0], sesion)
        self.assertIs(validacion.call_args.args[0], sesion)
        self.assertEqual(extraccion.call_args.args[2].campos["folio"].valor, "F-8")
        self.assertEqual(validacion.call_args.args[1].resultado_sugerido, "humana")
        evento = sesion.add.call_args.args[0]
        self.assertIsInstance(evento, EventoBitacora)
        self.assertIn(evento.accion, ACCIONES_BITACORA)
        self.assertEqual(evento.datos["revision_evidencia"], informe)
        self.assertEqual(evento.datos["resultado_reglas_sobre_lecturas"], original)

    def test_repetir_guardado_no_duplica_evento_de_revision(self):
        tools = HerramientasReales(ContextoUsuario(usuario_id="dev-ana", rol="analista"))
        sesion = MagicMock()

        @contextmanager
        def abrir():
            yield sesion

        with patch("backend.grafo_casos.herramientas_reales.sesion", abrir), \
                patch.object(tools, "_caso", return_value=SimpleNamespace(estado="revision")):
            tools.guardar("F-9201", {}, {}, "", {}, revision_evidencia={"version": "prueba"})
        sesion.add.assert_not_called()
