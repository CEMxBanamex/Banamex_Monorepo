"""API de casos de factura y auditoría para el frontend."""
import hashlib
import logging
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Annotated

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import column, func, select, table
from sqlalchemy.exc import IntegrityError
from steward_datos.api.bitacora import EventoBitacoraOut, FiltrosDisponibles, ListarBitacoraSalida
from steward_datos.api.casos import (
    CampoDetalle, CasoDetalle, CasoResumen, CrearCasoEntrada, CrearCasoSalida, DecisionCasoEntrada,
    DecisionCasoSalida, EstadoCaso, EventoDetalle, HallazgoDetalle,
    ListarCasosSalida, MetricasBandeja, TipoCaso,
)
from steward_datos.contratos import ContextoUsuario
from steward_datos.db.models import Caso, Documento, EventoBitacora, Factura
from steward_datos.db.sesion import sesion, siguiente_id_caso
from steward_datos.tools.consultas_chat_seguras import CasoNoDisponible, consultar_caso, sesion_autorizada

from backend.api.autenticacion import resolver_usuario
from backend.api.subidas import _cliente_s3, nombre_seguro, prefijo_subida
from backend.grafo_casos.flujo_real import FlujoCasosReal
from backend.grafo_casos.herramientas_reales import HerramientasReales

router = APIRouter(prefix="/api", tags=["Casos"])
Usuario = Annotated[ContextoUsuario, Depends(resolver_usuario)]
TIPO_UI = {"factura": "Factura", "validacion": "Validación con políticas"}
V_CASOS = table("v_casos", column("caso_id"))
FLUJOS: dict[str, FlujoCasosReal] = {}
DECISION = Lock()
logger = logging.getLogger(__name__)
IMAGENES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".pdf": "application/pdf"}
MAX_IMAGEN = 15 * 1024 * 1024


@router.get("/casos", response_model=ListarCasosSalida)
def listar_casos(usuario: Usuario, tipo: TipoCaso | None = None, estado: EstadoCaso | None = None):
    archivo = select(Documento.nombre).where(Documento.caso_id == Caso.id, Documento.principal).limit(1).scalar_subquery()
    base = Caso.id.in_(select(V_CASOS.c.caso_id))
    with sesion_autorizada(usuario) as s:
        grupos = s.execute(select(Caso.estado, func.count()).where(base).group_by(Caso.estado))
        conteos = {estado_db: cantidad for estado_db, cantidad in grupos}
        fila = select(Caso, archivo).where(base)
        if tipo:
            fila = fila.where(Caso.tipo == next(k for k, v in TIPO_UI.items() if v == tipo))
        if estado:
            fila = fila.where(Caso.estado == estado)
        casos = [
            CasoResumen(id=c.id, archivo=nombre or c.id, tipo=TIPO_UI[c.tipo], estado=c.estado,
                        resultado=c.resultado_final or c.resultado_sugerido, fecha=c.creado_en.isoformat(),
                        responsable=c.responsable_nombre)
            for c, nombre in s.execute(fila.order_by(Caso.creado_en.desc(), Caso.id.desc()))
        ]
    return ListarCasosSalida(
        casos=casos, metricas=MetricasBandeja(total=sum(conteos.values()), en_revision=conteos.get("revision", 0),
                                            revisados=conteos.get("revisado", 0), procesando=conteos.get("procesando", 0)),
    )


@router.get("/casos/{caso_id}", response_model=CasoDetalle)
def detalle_caso(caso_id: str, usuario: Usuario):
    try:
        c = consultar_caso(caso_id, usuario=usuario)
    except CasoNoDisponible as error:
        raise HTTPException(404, "Caso inexistente o sin acceso") from error
    except ValueError as error:
        raise HTTPException(422, "Identificador de caso inválido") from error
    documento_url = None
    with sesion_autorizada(usuario) as s:
        revision = s.scalar(select(EventoBitacora.datos).where(
            EventoBitacora.caso_id == c.id, EventoBitacora.caso_id.in_(select(V_CASOS.c.caso_id)),
            EventoBitacora.accion == "extraccion",
            EventoBitacora.datos["tipo"].astext == "revision_evidencia_experimental",
        ).order_by(EventoBitacora.id.desc()).limit(1))
        lectura = s.scalar(select(Factura.salida_cruda).where(
            Factura.caso_id == c.id, Factura.caso_id.in_(select(V_CASOS.c.caso_id)),
        ))
    informe = (revision or {}).get("revision_evidencia")
    evidencia_campos = (informe or {}).get("campos", {})
    if bucket := os.getenv("S3_BUCKET"):
        with sesion_autorizada(usuario) as s:
            clave = s.scalar(select(Documento.s3_key).where(
                Documento.caso_id == c.id, Documento.principal, Documento.caso_id.in_(select(V_CASOS.c.caso_id)),
            ))
        if clave and clave.startswith("casos/"):
            endpoint = os.getenv("S3_ENDPOINT_PUBLICO") or os.getenv("S3_ENDPOINT_URL") or None
            cliente = _cliente_s3(endpoint, os.getenv("AWS_REGION", "us-east-1"))
            documento_url = cliente.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": clave}, ExpiresIn=300)
    return CasoDetalle(
        documento_url=documento_url, id=c.id, archivo=c.archivo or c.id, tipo=TIPO_UI[c.tipo], estado=c.estado,
        resultado_sugerido=c.resultado_sugerido, resultado_final=c.resultado_final,
        explicacion=c.explicacion, fecha=c.creado_en.isoformat(), responsable=c.responsable or "",
        revision_evidencia=informe, conceptos=(lectura or {}).get("conceptos", []),
        campos=[CampoDetalle(id=x.campo, etiqueta=x.etiqueta or x.campo, valor=x.valor,
                             conf=x.confianza,
                             estado_evidencia=evidencia_campos.get(x.campo, {}).get("estado"),
                             valor_corregido=x.valor_corregido) for x in c.campos],
        hallazgos=[HallazgoDetalle(id=f"{h.regla_id}-{i}", tipo=h.severidad, titulo=h.titulo, texto=h.texto,
                                   regla=h.regla_id, version=h.regla_version, evidencia=h.evidencia or "",
                                   cifras=[list(cifra) for cifra in h.cifras] if h.cifras else None)
                   for i, h in enumerate(c.hallazgos)],
        eventos=[EventoDetalle(id=e.id, fecha=e.fecha.isoformat(), quien=e.actor, accion=e.accion, tono=e.tono,
                               detalle=e.detalle, regla=e.regla) for e in c.eventos],
    )


@router.get("/bitacora", response_model=ListarBitacoraSalida)
def listar_bitacora(usuario: Usuario, caso: str | None = None, quien: str | None = None, accion: str | None = None,
                    limite: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    e = EventoBitacora
    base = [] if usuario.rol == "administrador" else [e.caso_id.in_(select(V_CASOS.c.caso_id))]
    filtros = list(base)
    if caso:
        filtros.append(e.caso_id == caso.strip().upper())
    if quien:
        filtros.append(func.lower(e.actor_nombre).contains(quien.strip().lower(), autoescape=True))
    if accion:
        filtros.append(func.lower(e.accion).contains(accion.strip().lower(), autoescape=True))
    with sesion_autorizada(usuario) as s:
        total = s.execute(select(func.count()).select_from(e).where(*filtros)).scalar_one()
        filas = s.scalars(select(e).where(*filtros).order_by(e.fecha.desc(), e.id.desc()).offset(offset).limit(limite)).all()
        disponibles = [
            list(s.scalars(select(campo).where(*base, campo.is_not(None)).distinct().order_by(campo)))
            for campo in (e.caso_id, e.accion, e.actor_nombre)
        ]
        return ListarBitacoraSalida(
            eventos=[EventoBitacoraOut(id=f"EV-{x.id}", fecha=x.fecha.isoformat(), caso=x.caso_id,
                                       quien=x.actor_nombre, accion=x.accion, tono=x.tono, detalle=x.detalle,
                                       regla=f"{x.regla_id} · v{x.regla_version}" if x.regla_id else None) for x in filas],
            total=total, limite=limite, offset=offset,
            filtros=FiltrosDisponibles(casos=disponibles[0], acciones=disponibles[1], usuarios=disponibles[2]),
        )


def caso_ya_subido(s, clave: str, usuario: ContextoUsuario) -> CrearCasoSalida | None:
    anterior = s.execute(select(Caso.id, Caso.estado).join(Documento).where(
        Documento.s3_key == clave, Caso.responsable_id == usuario.usuario_id,
    )).first()
    if anterior:
        return CrearCasoSalida(id=anterior.id, estado=anterior.estado, mensaje="La factura ya fue recibida")
    return None


@router.post("/casos", response_model=CrearCasoSalida, status_code=201)
def crear_caso(entrada: CrearCasoEntrada, usuario: Usuario):
    if usuario.rol != "analista":
        raise HTTPException(403, "Solo un analista puede iniciar casos")
    if entrada.tipo != "Factura":
        raise HTTPException(422, "El grafo real admite casos de factura")
    try:
        nombre = nombre_seguro(entrada.archivo)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    mime = IMAGENES.get(Path(nombre).suffix.lower())
    if not mime:
        raise HTTPException(422, "Selecciona una factura PNG, JPEG o PDF")
    prefijo = prefijo_subida(usuario)
    if not entrada.s3_key or not re.fullmatch(f"{prefijo}[0-9a-f]{{32}}/{re.escape(nombre)}", entrada.s3_key):
        raise HTTPException(422, "Selecciona una factura subida con tu sesión")
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        raise HTTPException(503, "Almacenamiento no configurado")

    with sesion() as s:
        if anterior := caso_ya_subido(s, entrada.s3_key, usuario):
            return anterior
        caso_id = siguiente_id_caso(s, "factura")

    cliente = _cliente_s3(os.getenv("S3_ENDPOINT_URL") or None, os.getenv("AWS_REGION", "us-east-1"))
    try:
        obj = cliente.get_object(Bucket=bucket, Key=entrada.s3_key)
        with obj["Body"] as contenido:
            if not 0 < obj["ContentLength"] <= MAX_IMAGEN or obj.get("ContentType") != mime:
                raise HTTPException(422, "Tipo o tamaño de documento inválido")
            datos = contenido.read(MAX_IMAGEN + 1)
            if len(datos) != obj["ContentLength"]:
                raise HTTPException(422, "El archivo no se recibió completo")
    except ClientError as error:
        codigo = error.response["Error"]["Code"]
        if codigo in {"NoSuchKey", "404"}:
            raise HTTPException(404, "Archivo de subida inexistente") from error
        logger.exception("No fue posible recuperar la factura")
        raise HTTPException(503, "No se pudo leer el archivo subido") from error

    herramientas = HerramientasReales(usuario, documento={
        "nombre": nombre, "s3_key": entrada.s3_key, "mime": mime, "tamano_bytes": len(datos),
        "sha256": hashlib.sha256(datos).hexdigest(),
    })
    flujo = FlujoCasosReal(usuario, herramientas=herramientas, revisar_lecturas=True)
    with TemporaryDirectory() as carpeta:
        ruta = Path(carpeta, nombre)
        ruta.write_bytes(datos)
        try:
            flujo.procesar_caso(caso_id, str(ruta))
        except IntegrityError as error:
            with sesion() as s:
                if anterior := caso_ya_subido(s, entrada.s3_key, usuario):
                    return anterior
            logger.exception("No se pudo guardar el caso %s", caso_id)
            raise HTTPException(503, "No se pudo guardar el caso") from error
        except Exception as error:
            logger.exception("No se completó el grafo de casos para %s", caso_id)
            raise HTTPException(503, "No se completó el análisis de la factura") from error
    FLUJOS[caso_id] = flujo
    return CrearCasoSalida(id=caso_id, estado="revision", mensaje="Factura lista para revisión")


@router.post("/casos/{caso_id}/decision", response_model=DecisionCasoSalida)
def registrar_decision(caso_id: str, entrada: DecisionCasoEntrada, usuario: Usuario):
    if usuario.rol != "analista":
        raise HTTPException(403, "Solo un analista puede decidir casos")
    motivo = (entrada.comentario or "").strip()
    if entrada.accion != "confirmar" or entrada.resultado is None or not motivo:
        raise HTTPException(422, "Confirma una decisión de aceptación o rechazo e indica el motivo")

    caso_id = caso_id.strip().upper()
    decision = {"resultado": entrada.resultado, "motivo": motivo}
    with DECISION:
        flujo = FLUJOS.get(caso_id)
        if flujo is not None and flujo.usuario.usuario_id != usuario.usuario_id:
            raise HTTPException(404, "Caso inexistente o sin acceso")
        try:
            if flujo is not None:
                evento = flujo.reanudar_caso(caso_id, decision)["evento_decision_id"]
                FLUJOS.pop(caso_id, None)
            else:
                # Tras un reinicio, el único paso posterior a la pausa es el cierre ya persistido en PostgreSQL.
                evento = HerramientasReales(usuario).cerrar(caso_id, decision)
        except PermissionError as error:
            raise HTTPException(404, "Caso inexistente o sin acceso") from error
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
    return DecisionCasoSalida(caso_id=caso_id, estado="revisado", resultado_final=entrada.resultado,
                              evento_id=f"EV-{evento}", mensaje="Decisión registrada")
