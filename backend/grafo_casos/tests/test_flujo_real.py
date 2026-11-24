from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.grafo_casos.flujo_real import FlujoCasosReal
from steward_datos.contratos import CampoLeido, ContextoUsuario, FacturaExtraida, BuscarPoliticasSalida, ResultadoValidacion
from steward_datos.reglas.motor import Contexto, validar_factura
from steward_datos.validador import preparar_para_redactor


class AdaptadorPrueba:
    def __init__(self):
        self.guardados, self.cerrados, self.errores = [], [], []
        self.revisiones = []

    def iniciar(self, caso):
        return caso

    def validar(self, caso, factura, sha, fecha):
        return validar_factura(caso, FacturaExtraida.model_validate(factura),
                              Contexto(antecedentes=[], fecha_recepcion=date.fromisoformat(fecha)))

    def politicas(self, resultado, fecha):
        from steward_datos.contratos import ResultadoValidacion
        salida = preparar_para_redactor(ResultadoValidacion.model_validate(resultado), 1,
                                        buscar=lambda _: BuscarPoliticasSalida(
                                            fragmentos=[], modelo_embedding="prueba", sin_resultados=True))
        return salida.model_dump(mode="json"), {}

    def guardar(self, *datos, **revision):
        self.guardados.append(datos)
        self.revisiones.append(revision)

    def cerrar(self, *datos):
        self.cerrados.append(datos)

    def error(self, caso):
        self.errores.append(caso)


class TestFlujoReal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archivo = Path(self.tmp.name) / "imagen.png"
        self.archivo.write_bytes(b"contenido controlado por el extractor de prueba")
        self.tools = AdaptadorPrueba()
        self.usuario = ContextoUsuario(usuario_id="dev-ana", rol="analista")
        self.factura = FacturaExtraida(campos={"subtotal": CampoLeido(valor="100"),
                                              "impuestos": CampoLeido(valor="16"),
                                              "total": CampoLeido(valor="120"),
                                              "moneda": CampoLeido(valor="MXN")})
        self.flujo = FlujoCasosReal(self.usuario, herramientas=self.tools, extraer=lambda _: self.factura)

    def test_pausa_con_reglas_reales_y_cierra_solo_tras_decision(self):
        pausa = self.flujo.procesar_caso("F-9001", str(self.archivo))
        self.assertIn("__interrupt__", pausa)
        self.assertTrue(pausa["resultado"]["hallazgos"])
        self.assertEqual(len(self.tools.guardados), 1)
        self.assertEqual(self.tools.cerrados, [])
        self.assertNotIn("decision_analista", pausa)
        self.assertIn("Solo cita del catálogo", pausa["explicacion"])
        with self.assertRaises(ValidationError):
            self.flujo.reanudar_caso("F-9001", {"resultado": "humana", "motivo": ""})
        final = self.flujo.reanudar_caso("F-9001", {"resultado": "rechazado", "motivo": "Revisé la imagen."})
        self.assertNotIn("__interrupt__", final)
        self.assertEqual(final["resultado"], pausa["resultado"])
        self.assertEqual(len(self.tools.cerrados), 1)
        with self.assertRaises(ValueError):
            self.flujo.reanudar_caso("F-9001", {"resultado": "aceptado", "motivo": "Otra decisión"})

    def test_fallo_de_extraccion_no_fabrica_resultado(self):
        def fallar(_):
            raise RuntimeError("Ollama no disponible")
        flujo = FlujoCasosReal(self.usuario, herramientas=self.tools, extraer=fallar)
        with self.assertRaises(RuntimeError):
            flujo.procesar_caso("F-9002", str(self.archivo))
        self.assertEqual(self.tools.errores, ["F-9002"])
        self.assertEqual(self.tools.guardados, [])
        self.assertEqual(self.tools.cerrados, [])

    def test_casos_aislados_y_rol(self):
        for caso in ("F-9001", "F-9002"):
            self.flujo.procesar_caso(caso, str(self.archivo))
        self.flujo.reanudar_caso("F-9002", {"resultado": "rechazado", "motivo": "Verificado"})
        self.assertTrue(self.flujo._grafo.get_state(self.flujo._config("F-9001")).interrupts)
        with self.assertRaises(PermissionError):
            FlujoCasosReal(ContextoUsuario(usuario_id="admin", rol="administrador"))

    def test_revision_conserva_lecturas_guarda_informe_y_fuerza_pausa_humana(self):
        factura = FacturaExtraida(campos={"folio": CampoLeido(valor="F-8", etiqueta="Folio")},
                                  texto_completo="transcripción incompleta")
        # Incluso si las reglas sugieren aceptar, una lectura pendiente no lo habilita.
        with patch.object(self.tools, "validar", return_value=ResultadoValidacion(
                caso_id="F-9201", reglas_evaluadas=[], hallazgos=[],
                resultado_sugerido="aceptado", motivo="Fixture de reglas conforme")) as validar, \
                patch("backend.grafo_casos.flujo_real.extraer_campos_factura", return_value=factura) as extraer:
            flujo = FlujoCasosReal(self.usuario, herramientas=self.tools, revisar_lecturas=True)
            pausa = flujo.procesar_caso("F-9201", str(self.archivo))
        extraer.assert_called_once_with(str(self.archivo.resolve()), conservar_lecturas=True)
        self.assertEqual(validar.call_args.args[1]["campos"]["folio"]["valor"], "F-8")
        self.assertEqual(pausa["factura"]["campos"]["folio"]["valor"], "F-8")
        self.assertEqual(pausa["revision_evidencia"]["campos"]["folio"]["estado"], "pendiente_revision")
        self.assertEqual(pausa["resultado_reglas"]["resultado_sugerido"], "aceptado")
        self.assertEqual(pausa["resultado"]["resultado_sugerido"], "humana")
        self.assertEqual(pausa["__interrupt__"][0].value["resultado_sugerido"], "humana")
        self.assertIn("folio: 'F-8'", pausa["explicacion"])
        self.assertIn("revision_evidencia", self.tools.revisiones[0])
        self.assertEqual(self.tools.guardados[0][2]["resultado_sugerido"], "humana")
        self.assertEqual(self.tools.cerrados, [])
        final = flujo.reanudar_caso("F-9201", {"resultado": "rechazado", "motivo": "Lectura revisada."})
        self.assertNotIn("__interrupt__", final)
        self.assertEqual(len(self.tools.cerrados), 1)

    def test_revision_no_oculta_hallazgos_de_reglas_reales(self):
        flujo = FlujoCasosReal(self.usuario, herramientas=self.tools,
                               extraer=lambda _: self.factura, revisar_lecturas=True)
        pausa = flujo.procesar_caso("F-9202", str(self.archivo))
        self.assertEqual(pausa["resultado"]["resultado_sugerido"], "humana")
        self.assertTrue(pausa["resultado_reglas"]["hallazgos"])
        self.assertEqual(pausa["resultado"]["hallazgos"], pausa["resultado_reglas"]["hallazgos"])

    def test_modo_habitual_no_agrega_revision_experimental(self):
        pausa = self.flujo.procesar_caso("F-9203", str(self.archivo))
        self.assertNotIn("revision_evidencia", pausa)
        self.assertNotIn("resultado_reglas", pausa)
        self.assertEqual(self.tools.revisiones, [{}])
