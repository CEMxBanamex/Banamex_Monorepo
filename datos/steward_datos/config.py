"""Configuración del frente de Datos, leída de variables de entorno."""
import os
from pathlib import Path

RAIZ_DATOS = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/steward")

# Modelo elegido en el vault (modelos/decision-modelo-embeddings-embeddinggemma). Cambiar la dimensión requiere una migración.
EMBEDDING_MODELO = os.getenv("EMBEDDING_MODELO", "embeddinggemma:300m")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# "ollama" en uso normal; "falso" solo para pruebas sin GPU (vectores deterministas por hash).
EMBEDDING_PROVEEDOR = os.getenv("EMBEDDING_PROVEEDOR", "ollama")

UMBRAL_CONFIANZA = int(os.getenv("UMBRAL_CONFIANZA", "80"))

CATALOGO_REGLAS = RAIZ_DATOS / "reglas" / "catalogo.yaml"
CARPETA_POLITICAS = RAIZ_DATOS / "politicas"
CARPETA_SINTETICOS = RAIZ_DATOS / "sinteticos"
