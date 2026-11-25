"""URL prefirmada para que el navegador suba el archivo de un caso directo a S3 (S3-04).

El archivo no pasa por el backend (decisión arquitectura/decision-subida-directa-a-s3 del vault):
1. El frontend pide aquí una URL con el nombre del archivo y el tipo de caso.
2. Sube el archivo con `PUT <upload_url>` con la cabecera `Content-Type` que devuelve este endpoint e `If-None-Match: *`.
3. Crea el caso con el `s3_key` que recibió.

Generar la URL no llama a AWS: boto3 la firma en local con las credenciales disponibles (el perfil de la EC2 en dev
y prod; las falsas del docker-compose en local). Variables:
- S3_BUCKET: bucket del ambiente (en AWS llega desde SSM, /dsa/<env>/s3_bucket).
- AWS_REGION: región del bucket.
- S3_ENDPOINT_PUBLICO o S3_ENDPOINT_URL: solo local (SeaweedFS). La firma incluye el host, así que debe ser la
  dirección que ve el navegador (http://localhost:8333), no la de la red de Docker (http://s3:8333).
- S3_URL_SUBIDA_SEGUNDOS: vigencia de la URL (900 por omisión).
"""
import hashlib
import os
import re
import uuid
from functools import lru_cache
from pathlib import PurePath
from typing import Annotated, Literal

import boto3
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from steward_datos.contratos import ContextoUsuario

from backend.api.autenticacion import resolver_usuario

router = APIRouter(prefix="/api/casos", tags=["Casos"])

TipoDocumento = Literal["Factura", "Validación con políticas"]

# Extensión -> Content-Type. La Historia 1 recibe facturas (PDF o imagen); la Historia 2, registros en CSV o Excel
# y su documento de política en PDF.
TIPOS_CONTENIDO = {
    ".pdf": "application/pdf",
    ".xml": "application/xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}
EXTENSIONES_POR_TIPO: dict[str, set[str]] = {
    "Factura": {".pdf", ".png", ".jpg", ".jpeg", ".xml"},
    "Validación con políticas": {".csv", ".xlsx", ".xls", ".pdf"},
}
TAMANO_MAXIMO_BYTES = 20 * 1024 * 1024
_CARACTER_NO_PERMITIDO = re.compile(r"[^A-Za-z0-9._-]+")


class UrlSubidaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre_archivo: str = Field(min_length=1, max_length=255)
    tipo_documento: TipoDocumento
    # Opcional para no romper al frontend actual. Si viene, se valida contra el máximo. Es una revisión de cortesía:
    # una URL de PUT no puede imponer el tamaño (eso requeriría un POST prefirmado con content-length-range).
    tamano_bytes: int | None = Field(default=None, gt=0)


class UrlSubidaSalida(BaseModel):
    upload_url: str
    s3_key: str
    expira_en_segundos: int
    # El navegador debe mandar exactamente esta cabecera en el PUT: va dentro de la firma.
    content_type: str


def nombre_seguro(nombre: str) -> str:
    """Solo el nombre final, sin rutas, con letras, números, punto, guion y guion bajo. Máximo 100 caracteres."""
    base = PurePath(nombre.replace("\\", "/")).name
    limpio = _CARACTER_NO_PERMITIDO.sub("_", base).strip("._")
    if not limpio:
        raise ValueError("Nombre de archivo vacío")
    raiz, punto, extension = limpio.rpartition(".")
    if not punto:
        return limpio[:100]
    return f"{raiz[: 99 - len(extension)]}.{extension}"


@lru_cache(maxsize=1)
def _cliente_s3(endpoint: str | None, region: str):
    configuracion = Config(
        signature_version="s3v4",
        # SeaweedFS (local) solo entiende el estilo de ruta; en AWS se usa el estilo de host virtual.
        s3={"addressing_style": "path" if endpoint else "virtual"},
    )
    return boto3.client("s3", region_name=region, endpoint_url=endpoint or None, config=configuracion)


def prefijo_subida(usuario: ContextoUsuario) -> str:
    identidad = hashlib.sha256(usuario.usuario_id.encode()).hexdigest()
    return f"casos/{identidad}/"


def firmar_subida(entrada: UrlSubidaEntrada, usuario: ContextoUsuario) -> UrlSubidaSalida:
    bucket = os.getenv("S3_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("Falta S3_BUCKET")

    nombre = nombre_seguro(entrada.nombre_archivo)
    extension = PurePath(nombre).suffix.lower()
    if extension not in EXTENSIONES_POR_TIPO[entrada.tipo_documento]:
        permitidas = ", ".join(sorted(EXTENSIONES_POR_TIPO[entrada.tipo_documento]))
        raise ValueError(f"Extensión no permitida para {entrada.tipo_documento}: usa {permitidas}")
    if entrada.tamano_bytes is not None and entrada.tamano_bytes > TAMANO_MAXIMO_BYTES:
        raise ValueError(f"El archivo supera el máximo de {TAMANO_MAXIMO_BYTES // (1024 * 1024)} MB")

    content_type = TIPOS_CONTENIDO[extension]
    s3_key = f"{prefijo_subida(usuario)}{uuid.uuid4().hex}/{nombre}"
    segundos = int(os.getenv("S3_URL_SUBIDA_SEGUNDOS", "900"))
    endpoint = os.getenv("S3_ENDPOINT_PUBLICO") or os.getenv("S3_ENDPOINT_URL") or None
    cliente = _cliente_s3(endpoint, os.getenv("AWS_REGION", "us-east-1"))
    upload_url = cliente.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": s3_key, "ContentType": content_type, "IfNoneMatch": "*"},
        ExpiresIn=segundos,
        HttpMethod="PUT",
    )
    return UrlSubidaSalida(upload_url=upload_url, s3_key=s3_key, expira_en_segundos=segundos, content_type=content_type)


@router.post("/url-subida", response_model=UrlSubidaSalida)
def generar_url_subida(
    entrada: UrlSubidaEntrada, usuario: Annotated[ContextoUsuario, Depends(resolver_usuario)],
) -> UrlSubidaSalida:
    """URL prefirmada de PUT para subir el archivo de un caso directo al bucket del ambiente."""
    try:
        return firmar_subida(entrada, usuario)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="El almacenamiento no está configurado") from error
