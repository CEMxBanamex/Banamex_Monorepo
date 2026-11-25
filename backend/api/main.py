"""Aplicación FastAPI para Data Steward Agéntico."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.casos import router as casos_router
from backend.api.chat import router as chat_router
from backend.api.subidas import router as subidas_router

app = FastAPI(title="Data Steward Agéntico")

app.include_router(subidas_router)
app.include_router(casos_router)
app.include_router(chat_router)

origenes = [
    origen.strip()
    for origen in os.getenv("CORS_ORIGINS", "").split(",")
    if origen.strip()
]

if origenes:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/health")
def health() -> dict:
    """Comprueba que el proceso está activo."""
    return {"status": "ok"}
