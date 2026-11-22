# Tailscale: conectar AWS y las laptops con GPU

Los modelos (Ollama) corren en las laptops del equipo. Tailscale crea una red privada entre esas laptops y las EC2 de AWS, para que el backend llegue a Ollama sin exponerlo a internet. **Ollama no tiene contraseña: nunca debe ser alcanzable fuera de Tailscale.**

| Quién | Qué hace | Sección |
|---|---|---|
| Administrador de la tailnet (Juan Pablo) | Crea la tailnet, las etiquetas, la regla de acceso y las llaves | [1](#1-administrador-preparar-la-tailnet) |
| Integrantes con GPU que sirven un modelo | Instalan Tailscale y Ollama, y abren el 11434 solo para Tailscale | [2](#2-laptop-con-gpu-servir-un-modelo) |
| Integrantes sin modelo asignado | Instalan Tailscale para usar los modelos desde su entorno local | [3](#3-laptop-sin-modelo-solo-usar-los-modelos) |

## Etiquetas

Cada dispositivo entra a la tailnet con una etiqueta. La etiqueta decide qué puede hacer, no la persona.

| Etiqueta | Dispositivos | Puede llegar a |
|---|---|---|
| `tag:gpu` | Laptops que sirven un modelo (visión, chat, embeddings o respaldo) | Ollama de las otras laptops `tag:gpu` |
| `tag:equipo` | Laptops del equipo que no sirven un modelo | Ollama de las laptops `tag:gpu` |
| `tag:aws` | Las EC2 de dev y prod | Ollama de las laptops `tag:gpu` |

Nadie puede llegar a ningún otro puerto de nadie. El reparto actual de modelos está en el vault (`modelos/inventario-gpus-y-reparto-modelos`).

---

## 1. Administrador: preparar la tailnet

Una sola vez, desde la consola web de Tailscale.

### 1.1 Regla de acceso

En **Access controls**, reemplaza todo el contenido por esto (la regla por defecto permite todo). Es JSON con comentarios, que Tailscale acepta:

```jsonc
{
  // Solo el administrador puede asignar etiquetas.
  "tagOwners": {
    "tag:aws":    ["autogroup:admin"],
    "tag:gpu":    ["autogroup:admin"],
    "tag:equipo": ["autogroup:admin"]
  },

  // Lo único permitido: llegar a Ollama (11434) de las laptops con GPU.
  "acls": [
    {
      "action": "accept",
      "src":    ["tag:aws", "tag:gpu", "tag:equipo"],
      "dst":    ["tag:gpu:11434"]
    }
  ],

  // Tailscale revisa estas pruebas al guardar; si alguna falla, no deja guardar.
  "tests": [
    {
      "src":    "tag:aws",
      "accept": ["tag:gpu:11434"],
      "deny":   ["tag:gpu:22", "tag:gpu:3389", "tag:equipo:11434"]
    }
  ]
}
```

Si la consola marca error en el bloque `tests`, bórralo: es solo una comprobación y la regla funciona sin él.

### 1.2 Llaves

En **Settings → Keys → Generate auth key**. Las llaves con etiqueta tienen dos ventajas: el dispositivo entra como parte de la tailnet y no como un usuario más (no cuenta para el límite de usuarios del plan gratuito), y no se desconecta cuando caduca su sesión.

| Para | Reusable | Ephemeral | Pre-approved | Tags | Cuántas |
|---|---|---|---|---|---|
| Las EC2 | Sí | **No** | Sí | `tag:aws` | 1 |
| Cada laptop con GPU | No | No | Sí | `tag:gpu` | Una por persona |
| Cada laptop sin modelo | No | No | Sí | `tag:equipo` | Una por persona |

- **Ephemeral en No:** las EC2 se apagan con el lab; una llave efímera haría que se borraran de la tailnet cada vez.
- **Expiración:** el máximo es 90 días; alcanza para el proyecto. La expiración es para *usar* la llave; los dispositivos que ya entraron siguen conectados.
- **Reparte cada llave por mensaje privado.** Nunca en el repo, el vault ni un chat grupal. Una llave no reusable deja de servir en cuanto se usa.

### 1.3 Guardar la llave de AWS en SSM

Después de aplicar `infra/terraform/envs/shared` (que crea el parámetro con el valor `CAMBIAR`), con las credenciales del lab cargadas. `read -s` evita que la llave quede en el historial de la terminal:

```bash
read -rsp "Llave de Tailscale para AWS: " LLAVE && echo
aws ssm put-parameter --overwrite --type SecureString \
  --name /dsa/shared/tailscale_authkey --value "$LLAVE"
unset LLAVE
```

Las EC2 la leen al arrancar (`deploy/user-data.sh`, Fase 4) y entran con los nombres `dsa-dev` y `dsa-prod`.

### 1.4 Revisar

En **Machines** cada dispositivo debe mostrar su etiqueta y, en la columna de expiración, **Expiry disabled**. Si una laptop entró sin etiqueta, bórrala y que vuelva a entrar con su llave.

---

## 2. Laptop con GPU: servir un modelo

Instrucciones para Windows. Necesitas la llave `tag:gpu` que te mandó el administrador.

### 2.1 Entrar a la tailnet

1. Instala Tailscale desde tailscale.com/download.
2. Si ya usabas Tailscale con otra cuenta, cierra esa sesión: `tailscale logout`.
3. En PowerShell, cambia `<tu-nombre>` y pega tu llave:
   ```powershell
   tailscale up --auth-key=<LLAVE> --hostname=gpu-<tu-nombre>
   ```
4. Anota tu IP de Tailscale (empieza con `100.`); se la das a quien vaya a usar tu modelo:
   ```powershell
   tailscale ip -4
   ```

### 2.2 Ollama escuchando para la tailnet

Por defecto Ollama solo acepta conexiones de la misma laptop. Para que acepte las de la tailnet:

1. Configura la variable y **reinicia Ollama** (ícono junto al reloj → Quit, y vuelve a abrirlo):
   ```powershell
   setx OLLAMA_HOST "0.0.0.0:11434"
   ```
2. Descarga tu modelo con la etiqueta exacta acordada en el vault, por ejemplo:
   ```powershell
   ollama pull gemma3:4b
   ```

### 2.3 Firewall: el 11434 solo para Tailscale

`0.0.0.0` hace que Ollama escuche también en tu Wi-Fi (la del Tec, la de tu casa, una cafetería). El firewall de Windows debe dejar entrar al 11434 **solo desde Tailscale**.

- Si Windows te pregunta si permites Ollama en la red, elige **Cancelar**.
- En PowerShell **como administrador**:
  ```powershell
  # Quita cualquier permiso que se haya creado para Ollama en todas las redes.
  Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*ollama*" } | Remove-NetFirewallRule

  # Permite el 11434 solo desde direcciones de Tailscale (100.64.0.0/10).
  New-NetFirewallRule -DisplayName "Ollama solo Tailscale" -Direction Inbound `
    -Protocol TCP -LocalPort 11434 -RemoteAddress 100.64.0.0/10 -Action Allow
  ```

### 2.4 Comprobar

Desde **otra** laptop de la tailnet (o pídeselo a un compañero):

```powershell
curl.exe http://<tu-IP-de-Tailscale>:11434/api/tags
```

Debe responder con la lista de tus modelos. Si no responde: revisa que Ollama esté abierto, que `OLLAMA_HOST` se aplicó (reinicia Ollama) y que la regla del firewall existe.

**Tu laptop tiene que estar encendida, sin suspenderse y con Tailscale conectado** cuando el equipo pruebe o en la demo. En Windows: Configuración → Sistema → Energía → "Al estar conectado, suspender después de" → Nunca.

---

## 3. Laptop sin modelo: solo usar los modelos

1. Instala Tailscale y entra con tu llave `tag:equipo`:
   ```powershell
   tailscale up --auth-key=<LLAVE> --hostname=equipo-<tu-nombre>
   ```
2. En el `.env` del repo, apunta a la laptop que sirve el modelo, con su IP de Tailscale:
   ```
   OLLAMA_BASE_URL=http://<IP-de-Tailscale-de-la-laptop>:11434
   EMBEDDING_PROVEEDOR=ollama
   ```
3. Reinicia los contenedores: `make down && make up` (o `docker compose -f docker-compose.dev.yml up -d --build`).

Usa la IP (`100.x.y.z`) y no el nombre: los contenedores de Docker no siempre resuelven los nombres de Tailscale.

---

## Problemas comunes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `curl` se queda esperando | Ollama escucha solo en `127.0.0.1` | `setx OLLAMA_HOST "0.0.0.0:11434"` y reiniciar Ollama |
| `curl` responde "connection refused" | Ollama cerrado | Abrir Ollama |
| Funciona en la laptop pero no desde otra | Firewall de Windows | Repetir 2.3 |
| No funciona desde la laptop ni con el firewall bien | El dispositivo no tiene etiqueta o la regla de acceso no lo permite | Revisar su etiqueta en **Machines** |
| Las EC2 no llegan a Ollama | La laptop está suspendida o desconectada de Tailscale | Encenderla y revisar `tailscale status` |
| "Llave inválida" al entrar | La llave ya se usó o caducó | Pedir una nueva al administrador |

## Qué nunca hacer

- Publicar el puerto 11434 a internet (por ejemplo, con ngrok o abriéndolo en el router).
- Subir llaves de Tailscale al repo, al vault o a un chat grupal.
- Usar una llave efímera para las EC2.
