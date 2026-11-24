"""Rutas del historial persistente, limitado al propietario de la conversación."""

import logging
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.api.chat_stream import obtener_usuario_chat
from backend.api.historial_chat import (
    HistorialNoDisponible, _autorizar_caso, crear_conversacion,
    obtener_conversacion,
)
from steward_datos.contratos import ContextoUsuario
from steward_datos.db.models import Conversacion, Mensaje
from steward_datos.db.sesion import sesion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Historial del chat"])


class NuevaConversacion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    titulo: str = Field(min_length=1, max_length=200)
    caso_id: str | None = Field(default=None, min_length=1, max_length=100)


@contextmanager
def transaccion_historial():
    try:
        with sesion() as s:
            yield s
    except HistorialNoDisponible:
        raise HTTPException(404, "Conversación o caso no disponible") from None
    except SQLAlchemyError:
        logger.exception("No se pudo consultar o guardar el historial")
        raise HTTPException(503, "El historial no está disponible temporalmente") from None


def representar_conversacion(c):
    return {
        "id": str(c.id), "titulo": c.titulo, "caso_id": c.caso_id,
        "creada_en": c.creada_en, "actualizada_en": c.actualizada_en,
    }


@router.post("/conversaciones", status_code=201)
def nueva_conversacion(
    entrada: NuevaConversacion,
    usuario: ContextoUsuario = Depends(obtener_usuario_chat),
):
    with transaccion_historial() as s:
        c = crear_conversacion(s, usuario, entrada.titulo, entrada.caso_id)
        salida = representar_conversacion(c)
    return salida


@router.get("/conversaciones")
def listar_conversaciones(
    limite: int = Query(default=50, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    usuario: ContextoUsuario = Depends(obtener_usuario_chat),
):
    with transaccion_historial() as s:
        candidatas = s.scalars(
            select(Conversacion)
            .where(Conversacion.usuario_id == usuario.usuario_id)
            .order_by(Conversacion.actualizada_en.desc(), Conversacion.id)
            .offset(desplazamiento).limit(limite)
        )
        salida = []
        for c in candidatas:
            try:
                _autorizar_caso(s, usuario, c.caso_id)
            except HistorialNoDisponible:
                continue
            salida.append(representar_conversacion(c))
    return salida


@router.get("/conversaciones/{conversacion_id}/mensajes")
def consultar_historial(
    conversacion_id: str,
    limite: int = Query(default=100, ge=1, le=200),
    despues_de: int = Query(default=0, ge=0),
    usuario: ContextoUsuario = Depends(obtener_usuario_chat),
):
    with transaccion_historial() as s:
        c = obtener_conversacion(s, usuario, conversacion_id)
        mensajes = list(s.scalars(
            select(Mensaje)
            .where(Mensaje.conversacion_id == c.id, Mensaje.id > despues_de)
            .order_by(Mensaje.id).limit(limite + 1)
        ))
        hay_mas = len(mensajes) > limite
        pagina = mensajes[:limite]
        salida = {
            "conversacion_id": str(c.id),
            "mensajes": [{
                "id": str(m.id), "rol": m.rol, "contenido": m.contenido,
                "pasos": m.pasos, "citas": m.citas or [],
                "duracion_ms": m.duracion_ms, "creado_en": m.creado_en,
            } for m in pagina],
            "hay_mas": hay_mas,
            "siguiente_despues_de": str(pagina[-1].id) if hay_mas else None,
        }
    return salida
