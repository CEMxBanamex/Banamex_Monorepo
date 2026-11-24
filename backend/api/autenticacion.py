
"""Autenticación del backend: desarrollo local o Amazon Cognito."""

import os
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient, PyJWTError
from jwt.exceptions import PyJWKClientError

from steward_datos.contratos import ContextoUsuario

ROLES_VALIDOS = {"analista", "administrador"}


def _error_autenticacion() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="No fue posible autenticar al usuario",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _error_autorizacion() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail="El usuario no tiene un rol válido asignado",
    )


def _obtener_issuer() -> str:
    region = os.getenv("AWS_REGION", "us-east-1")
    user_pool_id = os.getenv("COGNITO_USER_POOL_ID", "").strip()

    if not user_pool_id:
        raise HTTPException(
            status_code=503,
            detail="Falta configurar COGNITO_USER_POOL_ID",
        )

    return f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"


@lru_cache(maxsize=4)
def _cliente_jwks(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True)


def _usuario_desde_cognito(token: str) -> ContextoUsuario:
    issuer = _obtener_issuer()
    client_id = os.getenv("COGNITO_CLIENT_ID", "").strip()

    if not client_id:
        raise HTTPException(
            status_code=503,
            detail="Falta configurar COGNITO_CLIENT_ID",
        )

    try:
        jwks = _cliente_jwks(f"{issuer}/.well-known/jwks.json")
        signing_key = jwks.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=client_id,
            leeway=30,
            options={
                "require": [
                    "exp",
                    "iat",
                    "iss",
                    "sub",
                    "aud",
                    "token_use",
                ],
            },
        )
    except (PyJWTError, PyJWKClientError, OSError, TimeoutError) as error:
        raise _error_autenticacion() from error

    if claims.get("token_use") != "id":
        raise _error_autenticacion()

    usuario_id = claims.get("sub")
    if not isinstance(usuario_id, str) or not usuario_id:
        raise _error_autenticacion()

    grupos = claims.get("cognito:groups", [])

    if not isinstance(grupos, list):
        raise _error_autorizacion()

    roles = set(grupos) & ROLES_VALIDOS

    if len(roles) != 1:
        raise _error_autorizacion()

    return ContextoUsuario(
        usuario_id=usuario_id,
        rol=roles.pop(),
    )


def resolver_usuario(
    authorization: str | None = Header(default=None),
    x_usuario: str | None = Header(default=None, alias="X-Usuario"),
    x_rol: str | None = Header(default=None, alias="X-Rol"),
) -> ContextoUsuario:
    """Resuelve la identidad confiable para una petición HTTP."""

    modo = os.getenv("AUTH_MODE", "").strip().lower()

    if modo == "dev":
        if not x_usuario or not x_rol:
            raise _error_autenticacion()

        if x_rol not in ROLES_VALIDOS:
            raise _error_autorizacion()

        try:
            return ContextoUsuario(
                usuario_id=x_usuario,
                rol=x_rol,
            )
        except Exception as error:
            raise _error_autenticacion() from error

    if modo == "cognito":
        if not authorization:
            raise _error_autenticacion()

        esquema, separador, token = authorization.partition(" ")

        if (
            not separador
            or esquema.lower() != "bearer"
            or not token.strip()
        ):
            raise _error_autenticacion()

        return _usuario_desde_cognito(token.strip())

    raise HTTPException(
        status_code=503,
        detail="AUTH_MODE no está configurado correctamente",
    )
