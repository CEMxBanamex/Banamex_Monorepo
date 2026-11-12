# Atajos del entorno local. Cada objetivo es un comando de Docker Compose; el README tiene los equivalentes
# para quien trabaja en Windows sin WSL.
#
#   make up && make migrate && make datos

COMPOSE := docker compose -f docker-compose.dev.yml
RUFF    := docker run --rm -v "$(CURDIR)":/io -w /io ghcr.io/astral-sh/ruff:0.14.0

.PHONY: help up down logs ps migrate datos reset-db test lint fmt

help: ## Lista los objetivos
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

.env:
	cp .env.example .env
	@echo "Se creó .env a partir de .env.example."

up: .env ## Construye y levanta postgres, s3, mcp y backend
	$(COMPOSE) up -d --build --wait

down: ## Detiene los contenedores (los datos se conservan)
	$(COMPOSE) down

logs: ## Sigue los logs de todos los servicios
	$(COMPOSE) logs -f --tail=100

ps: ## Estado de los servicios
	$(COMPOSE) ps

migrate: .env ## Aplica las migraciones como steward_migraciones
	$(COMPOSE) run --rm migraciones

datos: .env ## Carga los datos sintéticos como steward_carga (base recién migrada)
	$(COMPOSE) run --rm carga

reset-db: .env ## Borra la base, la recrea, migra y carga datos
	$(COMPOSE) rm -s -f -v postgres
	docker volume rm -f dsa_pgdatos
	$(COMPOSE) up -d --wait postgres
	$(COMPOSE) run --rm migraciones
	$(COMPOSE) run --rm carga

test: .env ## Pruebas de datos/, backend/ y mcp/
	$(COMPOSE) run --rm pruebas
	$(COMPOSE) run --rm pruebas-mcp

lint: ## Revisa el estilo de Python con ruff (en contenedor)
	$(RUFF) check datos backend mcp
	docker run --rm -v "$(CURDIR)":/io -w /io/db ghcr.io/astral-sh/ruff:0.14.0 check .

fmt: ## Corrige automáticamente lo que ruff puede corregir
	$(RUFF) check --fix datos backend mcp
	docker run --rm -v "$(CURDIR)":/io -w /io/db ghcr.io/astral-sh/ruff:0.14.0 check --fix .
