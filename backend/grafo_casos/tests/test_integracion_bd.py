"""Integración opcional sobre una base local migrada y con semillas; no borra el esquema."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.grafo_casos.flujo_real import FlujoCasosReal
from steward_datos import config
from steward_datos.contratos import CampoLeido, ContextoUsuario, FacturaExtraida
from steward_datos.db.models import Caso, EventoBitacora, Hallazgo


@unittest.skipUnless(os.getenv("GRAFO_DATABASE_URL_PRUEBAS"), "Requiere base de pruebas migrada, semillas y embeddings falso-hash")
class TestIntegracionBD(unittest.TestCase):
    def test_tools_reales_guardan_hallazgos_y_decision_sin_duplicados(self):
        motor = create_engine(os.environ["GRAFO_DATABASE_URL_PRUEBAS"])
        self.addCleanup(motor.dispose)

        @contextmanager
        def abrir():
            with Session(motor) as s, s.begin():
                yield s

        caso_id = "F-" + str(int(uuid.uuid4().hex[:8], 16)).zfill(10)
        factura = FacturaExtraida(campos={
            "folio": CampoLeido(valor=caso_id), "moneda": CampoLeido(valor="MXN"),
            "subtotal": CampoLeido(valor="100"), "impuestos": CampoLeido(valor="16"), "total": CampoLeido(valor="120"),
        }, modelo="fixture-integracion")
        with tempfile.TemporaryDirectory() as tmp, patch("backend.grafo_casos.herramientas_reales.sesion", abrir), \
                patch.object(config, "EMBEDDING_PROVEEDOR", "falso"):
            imagen = Path(tmp) / "imagen.png"
            imagen.write_bytes(b"fixture sin inferencia")
            flujo = FlujoCasosReal(ContextoUsuario(usuario_id="dev-ana", rol="analista"), extraer=lambda _: factura)
            pausa = flujo.procesar_caso(caso_id, str(imagen))
            n_hallazgos = len(pausa["resultado"]["hallazgos"])
            self.assertGreater(n_hallazgos, 0)
            with abrir() as s:
                caso = s.get(Caso, caso_id)
                self.assertEqual(caso.estado, "revision")
                self.assertIsNone(caso.resultado_final)
                self.assertEqual(s.scalar(select(func.count()).select_from(Hallazgo).where(Hallazgo.caso_id == caso_id)), n_hallazgos)
                self.assertEqual(s.scalar(select(func.count()).select_from(EventoBitacora).where(
                    EventoBitacora.caso_id == caso_id, EventoBitacora.accion == "regla_aplicada")), n_hallazgos)
            # Repetir el guardado no duplica ni los hallazgos ni sus eventos.
            flujo.tools.guardar(caso_id, pausa["factura"], pausa["resultado"], pausa["explicacion"], pausa["fragmentos"])
            decision = {"resultado": "rechazado", "motivo": "Total revisado contra el documento."}
            flujo.reanudar_caso(caso_id, decision)
            flujo.tools.cerrar(caso_id, decision)
            with abrir() as s:
                caso = s.get(Caso, caso_id)
                self.assertEqual((caso.estado, caso.resultado_final, caso.revisado_por), ("revisado", "rechazado", "dev-ana"))
                self.assertEqual(s.scalar(select(func.count()).select_from(EventoBitacora).where(
                    EventoBitacora.caso_id == caso_id, EventoBitacora.accion == "confirmacion")), 1)
                self.assertEqual(s.scalar(select(func.count()).select_from(Hallazgo).where(Hallazgo.caso_id == caso_id)), n_hallazgos)
