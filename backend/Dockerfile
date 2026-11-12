# syntax=docker/dockerfile:1
# Imagen del backend (FastAPI + LangGraph). Contexto de build: la raíz del repo, porque usa datos/ (steward_datos).
#   docker build -f backend/Dockerfile -t dsa-backend .

# --- Etapa 1: dependencias en un entorno virtual ---
FROM python:3.12-slim-bookworm AS dependencias
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY datos/requirements.txt /tmp/req/datos.txt
COPY backend/grafo_casos/requirements.txt /tmp/req/grafo.txt
COPY backend/requirements.txt /tmp/req/backend.txt
# El backend es cliente MCP: usa el mismo SDK que el servidor.
COPY mcp/requirements.txt /tmp/req/mcp.txt
RUN pip install --no-cache-dir -r /tmp/req/datos.txt -r /tmp/req/grafo.txt -r /tmp/req/backend.txt -r /tmp/req/mcp.txt

# --- Etapa 2: imagen final, sin herramientas de build y con usuario sin privilegios ---
FROM python:3.12-slim-bookworm AS final
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/datos
# /app no va en PYTHONPATH: la carpeta mcp/ taparía al SDK `mcp`. uvicorn y `python -m` ya agregan el directorio actual.
RUN useradd --create-home --uid 10001 steward
WORKDIR /app
COPY --from=dependencias /opt/venv /opt/venv
COPY datos/ datos/
COPY backend/ backend/
USER steward
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
