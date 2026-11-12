"""Aplicación FastAPI. Por ahora solo /api/health para el entorno local, el CI y los despliegues.

Lo mínimo que necesita la infraestructura (Fase 1 de docs/ci-cd). Los endpoints de negocio los agrega el equipo de backend.
Ejecutar desde la raíz del repo: uvicorn backend.api.main:app
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Data Steward Agéntico")

origenes = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origenes:
    app.add_middleware(CORSMiddleware, allow_origins=origenes, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health() -> dict:
    """Responde 200 si el proceso está arriba. No consulta la base: lo usan los health checks de Docker."""
    return {"status": "ok"}
