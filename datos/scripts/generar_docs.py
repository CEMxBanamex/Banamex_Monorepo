"""Regenera la documentación que sale de los YAML (catálogo de reglas, vistas, métricas, glosario y calidad).

Uso:  python scripts/generar_docs.py
Escribe en docs/datos/. Correrlo después de cambiar cualquier YAML de reglas/, gobernanza/ o semantica/.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from steward_datos.gobernanza import catalogo_datos, glosario, metricas, reglas_calidad  # noqa: E402
from steward_datos.reglas.catalogo import catalogo  # noqa: E402

DOCS = RAIZ.parent / "docs" / "datos"
AVISO = "_Generado con `datos/scripts/generar_docs.py`. No lo edites a mano._\n"


def celda(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def reglas_md() -> str:
    c = catalogo()
    L = ["# Catálogo de reglas del piloto", "", AVISO,
         "Fuente: [`datos/reglas/catalogo.yaml`](../../datos/reglas/catalogo.yaml), única para `validar_reglas`, la tabla `reglas` y la verdad de referencia.", "",
         "Efecto: **rechazo** → Rechazado si no hay dudas · **revision** → Requiere revisión humana · La revisión tiene precedencia sobre el rechazo.", ""]
    for h, t in ((1, "Historia 1 · Facturas"), (2, "Historia 2 · Registros de clientes")):
        L += [f"## {t}", "", "| Regla | Versión | Nombre | Política | Efecto | Qué comprueba |", "|---|---|---|---|---|---|"]
        for r in c.de_historia(h):
            L.append(f"| {r.id} | {r.version} | {r.nombre} | {r.politica_id} v{r.politica_version} §{r.seccion.split('.')[0]} | {r.efecto} | {celda(r.descripcion)} |")
        L.append("")
    L.append("Parámetros globales: umbral de confianza {umbral_confianza} %, tolerancia de montos {tolerancia_montos}, "
             "tipo de cambio fijo {tipo_cambio_usd_mxn} MXN/USD.".format(**c.globales))
    return "\n".join(L) + "\n"


def vistas_md() -> str:
    cat = catalogo_datos()
    L = ["# Vistas consultables y catálogo de datos", "", AVISO,
         "Fuente: [`datos/gobernanza/catalogo_datos.yaml`](../../datos/gobernanza/catalogo_datos.yaml). Las vistas se crean en la migración `0002`.", "",
         "## Seguridad por fila", "",
         "Cada transacción fija el contexto con `SET LOCAL` (`steward_datos.contexto.fijar_en_bd`):", "",
         "```sql", "SELECT set_config('app.rol', 'analista', true), set_config('app.usuario', '<sub de Cognito>', true);", "```", "",
         "- `administrador` ve todas las entidades; `analista` solo las de `usuarios_entidades`; sin contexto o con otro rol, ninguna fila.",
         "- `v_clientes` enmascara RFC y correo para quien no es administrador.",
         "- El usuario `steward_consultas` (lo crea Infraestructura) solo tiene `SELECT` sobre las vistas y `statement_timeout` de 5 s.", "",
         "## Dueños por dominio (P-021)", "", "| Dominio | Data owner | Data steward |", "|---|---|---|"]
    for d, v in cat["dominios"].items():
        L.append(f"| {d} | {v['data_owner']} | {v['data_steward']} |")
    for t in [t for t in cat["tablas"] if t.get("consultable")]:
        dom = cat["dominios"][t["dominio"]]
        L += ["", f"## `{t['tabla']}` · {t['nombre_negocio']}", "", celda(t["descripcion"]), "",
              f"Dominio {t['dominio']} · data owner: {dom['data_owner']} · sensibilidad: **{t['sensibilidad']}** · origen: {celda(t['origen'])}", "",
              "| Columna | Tipo | Descripción | Sensibilidad |", "|---|---|---|---|"]
        for c in t["columnas"]:
            sens = c["sensibilidad"] + (" (enmascarada)" if c.get("enmascarada") else "")
            L.append(f"| `{c['columna']}` | {c['tipo']} | {celda(c['descripcion'])} | {sens} |")
    L += ["", "## Tablas internas (no consultables)", "", "| Tabla | Nombre | Dominio | Sensibilidad |", "|---|---|---|---|"]
    for t in [t for t in cat["tablas"] if not t.get("consultable")]:
        L.append(f"| `{t['tabla']}` | {t['nombre_negocio']} | {t['dominio']} | {t['sensibilidad']} |")
    return "\n".join(L) + "\n"


def metricas_md() -> str:
    m = metricas()
    L = ["# Capa semántica: métricas oficiales", "", AVISO,
         f"Fuente: [`datos/semantica/metricas.yaml`](../../datos/semantica/metricas.yaml) · versión {m['version']} · dueño: {m['dueno']}.", "",
         "`obtener_metrica` arma el SQL con estas piezas; el modelo solo elige métrica, dimensiones (hasta 2), filtros y fechas.", "",
         "| Métrica | Definición | Unidad | Vista | Dimensiones | Filtros |", "|---|---|---|---|---|---|"]
    for n, d in m["metricas"].items():
        L.append(f"| `{n}` | {celda(d['definicion'])} | {d['unidad']} | `{d['vista']}` | {', '.join(d['dimensiones'])} | "
                 f"{', '.join(d.get('filtros', {})) or '—'} |")
    return "\n".join(L) + "\n"


def glosario_md() -> str:
    g = glosario()
    L = ["# Glosario de negocio", "", AVISO, f"Fuente: [`datos/gobernanza/glosario.yaml`](../../datos/gobernanza/glosario.yaml) · actualizado {g['actualizado_en']}.", "",
         "| Término | Definición | Sinónimos | Dueño | Fuente |", "|---|---|---|---|---|"]
    for t in sorted(g["terminos"], key=lambda t: t["termino"].lower()):
        L.append(f"| **{t['termino']}** | {celda(t['definicion'])} | {', '.join(t.get('sinonimos', []))} | {t['dueno']} | {t.get('fuente') or ''} |")
    return "\n".join(L) + "\n"


def calidad_md() -> str:
    L = ["# Reglas de calidad de datos", "", AVISO, "Fuente: [`datos/gobernanza/calidad.yaml`](../../datos/gobernanza/calidad.yaml) · política P-022.", "",
         "| Regla | Tabla | Columna | Dimensión | Umbral | Descripción |", "|---|---|---|---|---:|---|"]
    for r in reglas_calidad():
        L.append(f"| {r['id']} | {r['tabla']} | {r.get('columna') or '—'} | {r['dimension']} | {r['umbral']} % | {celda(r['descripcion'])} |")
    return "\n".join(L) + "\n"


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    for nombre, fn in (("catalogo_reglas.md", reglas_md), ("vistas_y_catalogo.md", vistas_md), ("metricas.md", metricas_md),
                       ("glosario.md", glosario_md), ("calidad.md", calidad_md)):
        (DOCS / nombre).write_text(fn(), encoding="utf-8")
        print(f"docs/datos/{nombre}")


if __name__ == "__main__":
    main()
