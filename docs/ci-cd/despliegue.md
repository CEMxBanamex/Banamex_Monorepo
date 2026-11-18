# Despliegue a dev y prod

Cómo llega el código a AWS y a Vercel. Las piezas en el servidor están en [`deploy/README.md`](../../deploy/README.md) y la infraestructura en [`infra/terraform/README.md`](../../infra/terraform/README.md).

## El flujo

```
rama de tarea ──PR──► dev ──────────────────────────────► main
                       │  Deploy dev (automático)           │  Deploy prod (al fusionar dev → main con merge commit)
                       │  1. build: imágenes a GHCR          │  1. verificar: el SHA de dev existe y se desplegó bien en dev
                       │     (tags <sha> y dev)              │  2. promover: re-etiqueta esa imagen como vX.Y.Z y prod
                       │  2. backend: deploy.sh en la EC2    │  3. backend: deploy.sh en la EC2 de prod (SSM Run Command)
                       │     de dev (runner self-hosted)     │  4. frontend: Vercel producción (app.<DOMINIO>)
                       │  3. frontend: Vercel, dev.<DOMINIO> │  5. release vX.Y.Z con notas
```

- **Prod nunca reconstruye:** corre exactamente la imagen que se probó en dev.
- **GitHub no tiene credenciales de AWS.** El runner vive en la EC2 de dev y usa el perfil de la instancia; desde ahí despliega dev y le ordena a la EC2 de prod que despliegue.
- **Con el lab apagado**, el job `deploy-backend` espera en cola a que el runner vuelva a conectarse. El frontend y las imágenes sí se publican.
- **Si un despliegue falla**, `deploy.sh` deja corriendo la versión anterior.

## Configuración (una sola vez)

### En GitHub (Settings → Secrets and variables → Actions)

| Tipo | Nombre | Valor |
|---|---|---|
| Variable | `DOMINIO` | El dominio sin subdominio, por ejemplo `midominio.com` |
| Variable | `RUNNER_DEV_ACTIVO` | `true` **después** de registrar el runner (`scripts/runner/registrar.sh`). Mientras no exista, el despliegue del backend a dev se salta en vez de quedarse en cola 24 horas |
| Secreto | `VERCEL_TOKEN` | Token de Vercel: Account Settings → Tokens |
| Secreto | `VERCEL_ORG_ID` | ID del equipo (Team Settings → General) o de tu cuenta si el proyecto es personal |
| Secreto | `VERCEL_PROJECT_ID` | Project Settings → General → Project ID |

Atajo para los dos IDs: en `frontend/`, corre `npx vercel link` una vez y léelos en `.vercel/project.json` (esa carpeta no se sube).

### En Vercel
- Se reutiliza el proyecto del mockup (**Root Directory: `frontend`**). `frontend/vercel.json` apaga los despliegues automáticos por Git: ahora solo despliega GitHub Actions.
- **Domains:** agrega `app.<DOMINIO>` como dominio de producción y `dev.<DOMINIO>` como dominio extra (el workflow de dev le asigna cada despliegue nuevo). Vercel te dice qué registro crear en el registrador para cada uno.

### En GitHub Packages, después del primer despliegue a dev
Las imágenes `backend` y `mcp` se crean privadas. Hazlas **públicas** (página del paquete → Package settings → Change visibility) para que las EC2 las bajen sin token. No llevan secretos ni datos.

## Uso diario

| Quiero | Hago |
|---|---|
| Probar algo en dev | PR de mi rama a `dev`; al fusionar se despliega solo |
| Pasar a prod | PR de `dev` a `main`, una aprobación y **merge commit** (no squash) |
| Volver a desplegar dev | Actions → Deploy dev → Run workflow |
| Regresar prod a una versión anterior | Actions → Deploy prod → Run workflow, con `version` = la versión (por ejemplo `v0.1.3`). No corre migraciones |
| Ver qué versión corre | Releases del repo (prod) o el parámetro `/dsa/<env>/image_tag` en SSM |

**Antes del primer `dev` → `main`:** tiene que existir al menos un despliegue exitoso a dev de ese mismo commit; si no, `verificar` lo rechaza.
