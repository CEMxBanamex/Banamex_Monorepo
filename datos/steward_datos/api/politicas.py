"""Endpoint de políticas para el rol administrador (tarea 3.2.1).

Se monta en la app de FastAPI del backend:
    from steward_datos.api.politicas import crear_router
    app.include_router(crear_router(get_usuario_actual), prefix="/api")

`get_usuario_actual` es la dependencia de Infraestructura (1.1.1); debe devolver un objeto con `nombre` y `rol`.
"""
from typing import Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from ..db.models import Politica
from ..db.sesion import sesion
from ..rag.embeddings import ErrorEmbeddings
from ..rag.ingesta import ingestar_politica

MAX_BYTES = 2_000_000


class PoliticaResumen(BaseModel):
    id: str
    version: str
    nombre: str
    estado: str
    vigente_desde: str
    vigente_hasta: str | None
    fragmentos: int


class RespuestaCarga(PoliticaResumen):
    accion: str


def _resumen(p: Politica) -> dict:
    return dict(id=p.id, version=p.version, nombre=p.nombre, estado=p.estado, vigente_desde=p.vigente_desde.isoformat(),
                vigente_hasta=p.vigente_hasta.isoformat() if p.vigente_hasta else None, fragmentos=len(p.fragmentos))


def crear_router(get_usuario_actual: Callable) -> APIRouter:
    router = APIRouter(tags=["políticas"])

    def solo_admin(usuario=Depends(get_usuario_actual)):
        if getattr(usuario, "rol", None) != "administrador":
            raise HTTPException(403, "Solo el rol administrador puede cargar políticas.")
        return usuario

    @router.get("/politicas", response_model=list[PoliticaResumen])
    def listar(_=Depends(get_usuario_actual)):
        with sesion() as s:
            return [_resumen(p) for p in s.scalars(select(Politica).order_by(Politica.id, Politica.version))]

    @router.post("/politicas", response_model=RespuestaCarga, status_code=201)
    async def cargar(archivo: UploadFile = File(...), usuario=Depends(solo_admin)):
        if not (archivo.filename or "").lower().endswith((".md", ".txt")):
            raise HTTPException(415, "Las políticas se cargan en Markdown (.md) con su bloque de metadatos.")
        contenido = await archivo.read()
        if len(contenido) > MAX_BYTES:
            raise HTTPException(413, "La política supera 2 MB.")
        try:
            texto = contenido.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(422, "El archivo no está en UTF-8.")
        try:
            with sesion() as s:
                p, accion = ingestar_politica(s, texto, archivo.filename, s3_key=f"politicas/{archivo.filename}",
                                              cargada_por=getattr(usuario, "nombre", "administrador"))
                return {**_resumen(p), "accion": accion}
        except ValueError as e:
            raise HTTPException(422, str(e))
        except ErrorEmbeddings as e:
            raise HTTPException(503, f"No se pudieron generar los embeddings: {e}")

    return router
