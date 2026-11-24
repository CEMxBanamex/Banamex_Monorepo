from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from backend.grafo_casos.comparar_vision import ejecutar, main, normalizado, puntuar, reportar, resumir


def documento(nombre="piloto_001.png"):
    return {"archivo": nombre, "verdad": {"campos": {"folio": "F-1", "total": "116.00"},
             "conceptos": [{"descripcion": "Servicio", "cantidad": "1", "precio_unitario": "100", "importe": "100"}]}}


def lectura():
    return {"campos": {"folio": {"valor": "F-1", "etiqueta": "Folio"},
                       "total": {"valor": "116.00", "etiqueta": "Total"}},
            "conceptos": documento()["verdad"]["conceptos"], "texto_completo": "Total 116.00"}


class TestCompararVision(unittest.TestCase):
    def test_errores_y_pendientes_no_desaparecen_del_denominador(self):
        documentos = [documento(), documento("piloto_002.pdf"), documento("piloto_003.png")]
        registros = {"piloto_001.png": {"estado": "ok", "sin_filtro": lectura()},
                     "piloto_002.pdf": {"estado": "error"}}
        r = puntuar(documentos, registros, "sin_filtro")
        self.assertEqual(r["precision_valores"], 1)
        self.assertEqual(r["recall_valores"], 1 / 3)
        self.assertEqual(r["documentos_14_campos_correctos"], 1)
        self.assertEqual(r["conceptos"]["recall_filas"], 1 / 3)
        self.assertEqual(r["por_campo"]["total"], {"correctos": 1, "total": 3})

    def test_filas_duplicadas_e_importes_inventados_no_mejoran_precision(self):
        salida = lectura()
        salida["campos"]["impuestos"] = {"valor": "16"}  # Ausente en esta referencia.
        salida["conceptos"] *= 2
        r = puntuar([documento()], {"piloto_001.png": {"estado": "ok", "sin_filtro": salida}}, "sin_filtro")
        self.assertEqual(r["precision_valores"], 2 / 3)
        self.assertEqual(r["conceptos"]["precision_filas"], 1 / 2)
        self.assertEqual(r["conceptos"]["documentos_tabla_exacta"], 0)
        self.assertEqual(r["errores_criticos_emitidos"], 1)

    def test_normaliza_sin_reparar_rfc_o_igualar_importes_invalidos(self):
        self.assertEqual(normalizado("total", "$ 1,000.00 MXN"), normalizado("total", "1000"))
        self.assertEqual(normalizado("tasa_iva", "IVA 16 %"), normalizado("tasa_iva", "16 %"))
        self.assertNotEqual(normalizado("emisor_rfc", "GSS07010186W"), normalizado("emisor_rfc", "GSS070101186W"))
        self.assertNotEqual(normalizado("total", "ilegible"), normalizado("total", None))

    def test_separa_ajuste_y_mide_perdida_del_filtro_sin_otra_inferencia(self):
        antes = lectura(); despues = deepcopy(antes); despues["campos"]["folio"]["valor"] = None
        documentos = [documento(), documento("piloto_002.pdf")]
        r = resumir(documentos, {"modelo": {"piloto_001.png": {
            "estado": "ok", "sin_filtro": antes, "filtro_anterior": despues, "segundos": 2}}}, ["modelo"])["modelo"]
        self.assertEqual(r["pendientes"], 1)
        self.assertEqual(r["grupos"]["usados_ajuste_qwen"]["sin_filtro"]["documentos"], 1)
        self.assertEqual(r["grupos"]["restantes"]["sin_filtro"]["documentos"], 1)
        self.assertGreater(r["grupos"]["todos"]["sin_filtro"]["recall_valores"],
                           r["grupos"]["todos"]["filtro_anterior"]["recall_valores"])
        with tempfile.TemporaryDirectory() as tmp:
            reportar(Path(tmp), documentos, {"modelo": {}}, ["modelo"])
            resumen = json.loads((Path(tmp) / "resumen.json").read_text(encoding="utf-8"))
            self.assertEqual(resumen["modelo"]["pendientes"], 2)
            self.assertTrue((Path(tmp) / "campos.csv").is_file())

    def test_captura_respuesta_cruda_incompleta_y_restaura_modelo(self):
        # Cliente HTTP simulado; no inicia Ollama ni necesita una GPU.
        cliente_real = httpx.Client
        respuestas = []
        def responder(request):
            respuestas.append(json.loads(request.content))
            return httpx.Response(200, json={"done": True, "done_reason": "length", "response": '{"campos":'})
        def cliente(**kwargs):
            return cliente_real(transport=httpx.MockTransport(responder), **kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            from PIL import Image
            archivo = Path(tmp) / "imagen.png"
            Image.new("RGB", (10, 10), "white").save(archivo)
            with patch.dict(os.environ, {"VISION_MODELO": "original"}), \
                    patch("backend.grafo_casos.comparar_vision.httpx.Client", side_effect=cliente):
                r = ejecutar(archivo, "modelo-prueba", "http://ollama")
                self.assertEqual(os.environ["VISION_MODELO"], "original")
        self.assertEqual(r["estado"], "error")
        self.assertEqual(r["respuesta_ollama"]["done_reason"], "length")
        self.assertEqual(respuestas[0]["model"], "modelo-prueba")
        self.assertNotIn("images", r["solicitud"])
        self.assertEqual(len(r["imagenes_enviadas_sha256"]), 1)

    def test_lote_reanuda_sin_repetir_y_guarda_ambas_etapas(self):
        cliente_real = httpx.Client
        llamadas = []
        def responder(request):
            if request.method == "GET":
                return httpx.Response(200, json={"models": [{"name": m, "digest": m} for m in ("modelo-a", "modelo-b")]})
            payload = json.loads(request.content)
            llamadas.append(payload)
            return httpx.Response(200, json={"done": True, "response": json.dumps(lectura())})
        def cliente(**kwargs):
            return cliente_real(transport=httpx.MockTransport(responder), **kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            from PIL import Image
            raiz = Path(tmp); entrada = raiz / "corpus"; entrada.mkdir(); salida = raiz / "salida"
            for i in (1, 2):
                nombre = f"piloto_{i:03d}.png"
                archivo = entrada / nombre
                Image.new("RGB", (10, 10), "white").save(archivo)
                d = {**documento(nombre), "sha256": hashlib.sha256(archivo.read_bytes()).hexdigest()}
                archivo.with_suffix(".json").write_text(json.dumps(d), encoding="utf-8")
            argumentos = ["comparar", "--salida", str(salida), "--corpus", str(entrada),
                          "--modelos", "modelo-a", "modelo-b"]
            with patch("backend.grafo_casos.comparar_vision.httpx.Client", side_effect=cliente), redirect_stdout(StringIO()):
                with patch("sys.argv", [*argumentos, "--limite", "1"]):
                    main()
                self.assertEqual(len(llamadas), 2)
                with patch("sys.argv", [*argumentos, "--reanudar"]):
                    main()
                self.assertEqual(len(llamadas), 4)
                with patch("sys.argv", [*argumentos, "--reanudar"]):
                    main()
                self.assertEqual(len(llamadas), 4)
            resumen = json.loads((salida / "resumen.json").read_text(encoding="utf-8"))
            self.assertEqual(resumen["modelo-a"]["pendientes"], 0)
            self.assertEqual(resumen["modelo-b"]["ok"], 2)
            for carpeta in ("modelo_1", "modelo_2"):
                registro = json.loads((salida / carpeta / "piloto_001.json").read_text(encoding="utf-8"))
                self.assertEqual(registro["sin_filtro"]["campos"]["folio"]["valor"], "F-1")
                self.assertIsNone(registro["filtro_anterior"]["campos"]["folio"]["valor"])
                self.assertIn("respuesta_ollama", registro)
            self.assertTrue(all("verdad" not in p and "esperado" not in p for p in llamadas))
