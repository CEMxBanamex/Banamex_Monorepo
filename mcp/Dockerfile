# syntax=docker/dockerfile:1
# Imagen del servidor MCP. Contexto de build: la raíz del repo, porque usa datos/ (steward_datos).
#   docker build -f mcp/Dockerfile -t dsa-mcp .
# En contenedor el servidor usa HTTP (streamable-http) en el puerto 8001, ruta /mcp, solo dentro de la red de Docker.

# --- Etapa 1: dependencias en un entorno virtual ---
FROM python:3.12-slim-bookworm AS dependencias
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY datos/requirements.txt /tmp/req/datos.txt
COPY mcp/requirements.txt /tmp/req/mcp.txt
# watchfiles: recarga en caliente en docker-compose.dev.yml.
RUN pip install --no-cache-dir -r /tmp/req/datos.txt -r /tmp/req/mcp.txt watchfiles==1.1.1

# --- Etapa 2: imagen final, sin herramientas de build y con usuario sin privilegios ---
FROM python:3.12-slim-bookworm AS final
# La carpeta mcp/ no se importa (chocaría con el SDK `mcp`); el paquete del servidor es mcp/steward_mcp/.
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/mcp:/app/datos \
    MCP_TRANSPORT=streamable-http \
    MCP_PORT=8001
RUN useradd --create-home --uid 10001 steward
WORKDIR /app
COPY --from=dependencias /opt/venv /opt/venv
COPY datos/ datos/
COPY mcp/ mcp/
USER steward
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os, socket; socket.create_connection(('127.0.0.1', int(os.environ['MCP_PORT'])), timeout=2).close()"]
CMD ["python", "-m", "steward_mcp.servidor"]
