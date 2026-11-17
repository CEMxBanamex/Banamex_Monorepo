# Despliegue en las EC2

Estos archivos viven en `/opt/dsa` de cada EC2 (dev y prod). Los deja ahí `user-data.sh` al crear la instancia y los actualiza `deploy.sh --ref <commit>` en cada despliegue.

| Archivo | Qué hace | Cuándo corre |
|---|---|---|
| `user-data.sh` | Instala Docker, Compose y Tailscale; baja estos archivos; instala el servicio `dsa-arranque` | Solo la primera vez que arranca la EC2 (lo conecta Terraform) |
| `arranque.sh` | Une la EC2 a Tailscale si falta, regenera `.env` desde SSM y levanta la versión vigente | En cada encendido del lab (servicio `dsa-arranque`) |
| `generar-env.sh` | Arma `/opt/dsa/.env` con `/dsa/<env>/*` y las contraseñas de `/dsa/shared/db/*` | Lo llaman `arranque.sh` y `deploy.sh` |
| `deploy.sh` | Baja la versión, migra, levanta y revisa `/api/health`; si falla, regresa a la anterior | En cada despliegue (pipeline de la Fase 5) |
| `docker-compose.yml` | Caddy (HTTPS), `backend` y `mcp`, más las tareas `migraciones`, `carga` y `recarga` | Lo usan los scripts |
| `Caddyfile` | Certificado de Let's Encrypt para `API_HOST` y proxy al backend, sin búfer para el SSE | Lo lee Caddy |

## Operación a mano (por Session Manager, como root)

```bash
cd /opt/dsa

# Estado y bitácoras
docker compose ps
docker compose logs --tail=100 backend
journalctl -u dsa-arranque -b          # lo que hizo el arranque en este encendido
cat /var/log/dsa-user-data.log         # lo que hizo la EC2 al crearse

# Desplegar o regresar a una versión
./deploy.sh <tag> dev
./deploy.sh <tag-anterior> dev --sin-migraciones

# Datos sintéticos: primera carga, o vaciar y volver a cargar
docker compose --profile tareas run --rm carga
docker compose --profile tareas run --rm recarga
```

En prod nadie carga ni edita datos a mano: se usa el mismo comando y la misma versión que ya se probó en dev.

## Qué necesita en SSM

- `/dsa/<env>/*`: lo crea Terraform (`api_host`, `db_host`, `image_registry`, ...). A mano: `ollama_base_url`. `image_tag` lo escribe `deploy.sh`.
- `/dsa/shared/db/<rol>`: contraseñas de los usuarios de servicio; las crea `scripts/db/crear-bases.sh`.
- `/dsa/shared/tailscale_authkey`: llave `tag:aws` de Tailscale (ver `docs/ci-cd/tailscale.md`).
