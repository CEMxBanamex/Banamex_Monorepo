"""Nodo validador del grafo de casos (dueña: Iris), en versión determinista.

validar_reglas decide el resultado y cada hallazgo ya trae su cita exacta del catálogo (política, versión y sección).
Aquí solo se agrega el texto de esa sección para que el Redactor lo cite. Se busca por regla, no por tipo de política:
R-002 se sustenta en P-011 (tipo gobernanza) y las reglas de la Historia 2 también, así que filtrar por tipo
`facturas` las dejaría sin política.
"""
from datetime import date
from typing import Callable, Optional

from pydantic import BaseModel

from .contratos import BuscarPoliticasEntrada, BuscarPoliticasSalida, HallazgoOut, ResultadoValidacion


class FragmentoCitado(BaseModel):
    politica_id: str
    version: str
    seccion: str
    texto: Optional[str] = None
    origen: str  # "rag" si el texto salió de buscar_politicas; "catalogo" si solo se tiene la cita


class HallazgoConPolitica(BaseModel):
    hallazgo: HallazgoOut
    politica: FragmentoCitado


class SalidaValidador(BaseModel):
    caso_id: str
    resultado_sugerido: str
    motivo: str
    reglas_evaluadas: list[str]
    hallazgos: list[HallazgoConPolitica]
    pasos: list[str]


def preparar_para_redactor(resultado: ResultadoValidacion, historia: int,
                           buscar: Callable[[BuscarPoliticasEntrada], BuscarPoliticasSalida],
                           fecha: Optional[date] = None) -> SalidaValidador:
    pasos = [f"Validando reglas… {len(resultado.reglas_evaluadas)} evaluadas, {len(resultado.hallazgos)} hallazgos"]
    salida = []
    cache: dict[str, Optional[FragmentoCitado]] = {}
    for h in resultado.hallazgos:
        if h.regla_id not in cache:
            r = buscar(BuscarPoliticasEntrada(consulta=h.titulo, k=5, reglas=[h.regla_id], historia=historia, fecha=fecha))
            f = next((x for x in r.fragmentos if x.politica_id == h.politica_id and x.version == h.politica_version
                      and x.seccion == h.politica_seccion), None)
            cache[h.regla_id] = None if f is None else FragmentoCitado(
                politica_id=f.politica_id, version=f.version, seccion=f.seccion, texto=f.texto, origen="rag")
            pasos.append(f"Buscando política de {h.regla_id}… {h.politica_id} v{h.politica_version}"
                         + ("" if f else " (solo cita del catálogo)"))
        cita = cache[h.regla_id] or FragmentoCitado(politica_id=h.politica_id, version=h.politica_version or "",
                                                     seccion=h.politica_seccion or "", origen="catalogo")
        salida.append(HallazgoConPolitica(hallazgo=h, politica=cita))
    return SalidaValidador(caso_id=resultado.caso_id, resultado_sugerido=resultado.resultado_sugerido,
                           motivo=resultado.motivo, reglas_evaluadas=resultado.reglas_evaluadas,
                           hallazgos=salida, pasos=pasos)
