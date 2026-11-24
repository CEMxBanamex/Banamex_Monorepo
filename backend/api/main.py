"""Aplicación FastAPI: chat, conversaciones y subida de archivos."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.chat_provisional import router as chat_provisional_router
from backend.api.chat_stream import router as chat_stream_router
from backend.api.conversaciones import router as conversaciones_router
from backend.api.subidas import router as subidas_router


app = FastAPI(title="Data Steward Agéntico")

app.include_router(chat_provisional_router)
app.include_router(chat_stream_router)
app.include_router(conversaciones_router)
app.include_router(subidas_router)

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
    """Confirma que el proceso responde."""
    return {"status": "ok"}