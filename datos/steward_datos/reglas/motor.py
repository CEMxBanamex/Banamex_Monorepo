"""Motor determinista de reglas. No usa LLM ni base de datos: recibe todo lo que necesita como argumentos.

La tool validar_reglas (tools/validar_reglas.py) consulta la base para armar el contexto
(padrón, entidades, antecedentes) y llama a estas funciones.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional

from ..contratos import (
    ETIQUETAS, Antecedente, FacturaExtraida, HallazgoOut, ResultadoValidacion, TablaRegistros,
)
from . import normalizar as n
from .catalogo import Catalogo, Regla, catalogo as catalogo_por_defecto

# Campos que participan en alguna regla; la baja confianza en ellos dispara R-003.
CAMPOS_EVALUADOS = ("folio", "fecha", "emisor_nombre", "emisor_rfc", "receptor_nombre", "receptor_rfc",
                    "moneda", "subtotal", "impuestos", "tasa_iva", "retenciones", "total")

PATRONES_INYECCION = [
    r"ignora(?:r)?\s+(?:las|todas\s+las|tus)\s+(?:instrucciones|reglas)",
    r"ignore\s+(?:all\s+|the\s+)?(?:previous|prior|above)\s+instructions",
    r"olvida\s+(?:las|tus)\s+(?:instrucciones|reglas)",
    r"(?:marca|clasifica|aprueba|acepta)\w*\s+(?:esta|la)\s+factura\s+como\s+(?:aceptada|aprobada|v[aá]lida)",
    r"(?:mark|classify)\s+(?:this|the)\s+invoice\s+as\s+(?:accepted|approved|valid)",
    r"(?:eres|act[uú]a\s+como)\s+(?:un|el)\s+(?:asistente|sistema|agente)",
    r"system\s*prompt|prompt\s+del\s+sistema|instrucciones\s+del\s+sistema",
    r"libera(?:r)?\s+(?:el\s+)?pago",
    r"no\s+(?:reportes|registres|menciones)\s+(?:este|ning[uú]n)\s+hallazgo",
]
RE_INYECCION = re.compile("|".join(PATRONES_INYECCION), re.IGNORECASE)


@dataclass
class Contexto:
    proveedores_activos: Optional[set[str]] = None  # None = no evaluar R-017
    entidades_receptoras: Optional[set[str]] = None  # None = no evaluar R-018
    antecedentes: list[Antecedente] = field(default_factory=list)
    sha256: Optional[str] = None
    fecha_recepcion: Optional[date] = None


class _Acumulador:
    def __init__(self, cat: Catalogo, caso_id: str):
        self.cat = cat
        self.caso_id = caso_id
        self.evaluadas: list[str] = []
        self.hallazgos: list[HallazgoOut] = []

    def evaluar(self, regla_id: str) -> Regla:
        r = self.cat[regla_id]
        if r.clave not in self.evaluadas:
            self.evaluadas.append(r.clave)
        return r

    def agregar(self, regla_id: str, titulo: str, texto: str, *, efecto: Optional[str] = None, **kw) -> None:
        r = self.cat[regla_id]
        efecto = efecto or r.efecto
        severidad = r.severidad if efecto == r.efecto else {"rechazo": "error", "revision": "adv", "informativo": "info"}[efecto]
        self.hallazgos.append(HallazgoOut(
            regla_id=r.id, regla_version=r.version, politica_id=r.politica_id,
            efecto=efecto, severidad=severidad, titulo=titulo, texto=texto, **kw,
        ))

    def resultado(self, motivo_ok: str) -> ResultadoValidacion:
        revision = [h for h in self.hallazgos if h.efecto == "revision"]
        rechazo = [h for h in self.hallazgos if h.efecto == "rechazo"]
        if revision:
            sugerido = "humana"
            motivo = "Requiere revisión humana por: " + "; ".join(dict.fromkeys(f"{h.regla_id} {self.cat[h.regla_id].nombre.lower()}" for h in revision))
        elif rechazo:
            sugerido = "rechazado"
            motivo = "No cumple: " + "; ".join(dict.fromkeys(f"{h.regla_id} {self.cat[h.regla_id].nombre.lower()}" for h in rechazo))
        else:
            sugerido = "aceptado"
            motivo = motivo_ok
        return ResultadoValidacion(caso_id=self.caso_id, reglas_evaluadas=self.evaluadas, hallazgos=self.hallazgos,
                                   resultado_sugerido=sugerido, motivo=motivo)


def _evidencia(f: FacturaExtraida, campo: str) -> tuple[str, Optional[dict]]:
    c = f.campos.get(campo)
    pagina = (c.pagina if c and c.pagina else 1)
    detalle = {"pagina": pagina, "campo": campo}
    if c and c.bbox:
        detalle["bbox"] = c.bbox
    return f"página {pagina}, {ETIQUETAS.get(campo, campo).lower()}", detalle


def _cuadra(esperado: Decimal, encontrado: Decimal, tolerancia: float) -> bool:
    return abs(esperado - encontrado) <= Decimal(str(tolerancia))


def _cifras(esperado: Decimal, encontrado: Decimal) -> list[tuple[str, str]]:
    return [("Esperado", n.formato_monto(esperado)), ("Encontrado", n.formato_monto(encontrado)),
            ("Diferencia", n.formato_monto(abs(encontrado - esperado)))]


def validar_factura(caso_id: str, f: FacturaExtraida, ctx: Optional[Contexto] = None,
                    cat: Optional[Catalogo] = None) -> ResultadoValidacion:
    cat = cat or catalogo_por_defecto()
    ctx = ctx or Contexto()
    acc = _Acumulador(cat, caso_id)
    g = cat.globales
    hoy = ctx.fecha_recepcion or date.today()
    valor = lambda c: (f.campos[c].valor if c in f.campos else None)

    r = acc.evaluar("R-031")
    tipo = (f.tipo_documento or "factura").lower()
    if tipo not in r.parametros.get("tipos", ["factura"]):
        acc.agregar("R-031", "No se encontró una regla aplicable a este caso",
                    f"El documento parece ser «{tipo.replace('_', ' ')}». Las políticas vigentes solo cubren facturas de "
                    "proveedores, así que el agente no puede sugerir un resultado. Una persona debe revisarlo.",
                    evidencia="documento completo")
        return acc.resultado("")

    # R-030 primero: el contenido sospechoso se reporta aunque las demás reglas se cumplan.
    acc.evaluar("R-030")
    textos = [f.texto_completo or ""] + [c.valor or "" for c in f.campos.values()] + [c.descripcion for c in f.conceptos]
    coincidencias = sorted({m.group(0) for t in textos for m in RE_INYECCION.finditer(t)})
    if coincidencias:
        acc.agregar("R-030", "El documento contiene instrucciones dirigidas al sistema",
                    "Se encontró texto que intenta dar órdenes al sistema. No se siguió y se evaluaron las reglas normalmente. "
                    "Una persona debe revisar el caso.",
                    cifras=[("Texto detectado", c[:60]) for c in coincidencias[:3]], evidencia="texto del documento",
                    evidencia_detalle={"coincidencias": coincidencias})

    r = acc.evaluar("R-001")
    faltan = [c for c in r.parametros["campos"] if n.vacio(valor(c))]
    if faltan:
        etiquetas = ", ".join(ETIQUETAS[c].lower() for c in faltan)
        acc.agregar("R-001", "Faltan datos obligatorios en la factura",
                    f"La factura no muestra: {etiquetas}. La política exige estos datos para toda factura de proveedor.",
                    campos=faltan, evidencia="página 1")

    acc.evaluar("R-002")
    for c in ("emisor_rfc", "receptor_rfc"):
        v = valor(c)
        if not n.vacio(v) and not n.rfc_valido(v):
            ev, det = _evidencia(f, c)
            acc.agregar("R-002", f"El {ETIQUETAS[c]} no tiene un formato válido",
                        f"«{v}» no corresponde a un RFC de persona moral (12 caracteres) ni de persona física (13), "
                        "o su fecha no existe.", campos=[c], evidencia=ev, evidencia_detalle=det)

    r = acc.evaluar("R-003")
    umbral = r.parametros.get("umbral", g.get("umbral_confianza", 80))
    for c in CAMPOS_EVALUADOS:
        campo = f.campos.get(c)
        if campo and not n.vacio(campo.valor) and campo.confianza is not None and campo.confianza < umbral:
            ev, det = _evidencia(f, c)
            acc.agregar("R-003", f"{ETIQUETAS[c]}: se leyó con baja confianza",
                        f"El campo se leyó con {campo.confianza} % de confianza (mínimo {umbral} %). "
                        "Verifícalo contra el documento original.", campos=[c], evidencia=ev, evidencia_detalle=det)

    r = acc.evaluar("R-004")
    fe = n.fecha(valor("fecha"))
    if not n.vacio(valor("fecha")):
        ev, det = _evidencia(f, "fecha")
        if fe is None:
            acc.agregar("R-004", "No se pudo interpretar la fecha de emisión",
                        f"«{valor('fecha')}» no es una fecha válida.", campos=["fecha"], evidencia=ev, evidencia_detalle=det)
        elif fe > hoy:
            acc.agregar("R-004", "La fecha de emisión es posterior a la recepción",
                        f"La factura tiene fecha {fe:%d/%m/%Y} y se recibió el {hoy:%d/%m/%Y}.",
                        campos=["fecha"], evidencia=ev, evidencia_detalle=det)
        elif (hoy - fe).days > r.parametros["antiguedad_max_dias"]:
            acc.agregar("R-004", "La factura es extemporánea",
                        f"Tiene {(hoy - fe).days} días de antigüedad; el máximo es {r.parametros['antiguedad_max_dias']}.",
                        campos=["fecha"], evidencia=ev, evidencia_detalle=det)

    r = acc.evaluar("R-005")
    moneda = (valor("moneda") or "").strip().upper()
    if moneda and moneda not in r.parametros["monedas"]:
        ev, det = _evidencia(f, "moneda")
        acc.agregar("R-005", "Moneda no admitida", f"La factura está en {moneda}. Solo se procesan MXN y USD; "
                    "Tesorería debe revisarla.", campos=["moneda"], evidencia=ev, evidencia_detalle=det)

    subtotal, impuestos, total = n.monto(valor("subtotal")), n.monto(valor("impuestos")), n.monto(valor("total"))
    retenciones = n.monto(valor("retenciones")) or Decimal("0.00")

    r = acc.evaluar("R-010")
    importes = [n.monto(c.importe) for c in f.conceptos]
    if subtotal is not None and importes and all(i is not None for i in importes):
        suma = sum(importes, Decimal("0.00"))
        if not _cuadra(suma, subtotal, r.parametros["tolerancia"]):
            ev, det = _evidencia(f, "subtotal")
            acc.agregar("R-010", "Los conceptos no suman el subtotal",
                        f"La suma de los {len(importes)} conceptos da un valor distinto al subtotal impreso.",
                        cifras=_cifras(suma, subtotal), campos=["subtotal"], evidencia=ev, evidencia_detalle=det)

    r = acc.evaluar("R-011")
    if subtotal is not None and impuestos is not None:
        tasas = [Decimal(str(t)) for t in r.parametros["tasas"]]
        declarada = n.tasa(valor("tasa_iva"))
        candidatas = [declarada] if declarada is not None else tasas
        ok = any(t in tasas and _cuadra((subtotal * t).quantize(Decimal("0.01")), impuestos, r.parametros["tolerancia"])
                 for t in candidatas)
        if not ok:
            ev, det = _evidencia(f, "impuestos")
            t = declarada if declarada is not None else Decimal("0.16")
            esperado = (subtotal * t).quantize(Decimal("0.01"))
            fuera = declarada is not None and declarada not in tasas
            acc.agregar("R-011", "La tasa de IVA no está admitida" if fuera else "Los impuestos no corresponden a una tasa admitida",
                        (f"La factura declara IVA de {declarada * 100:.0f} %, que no es una tasa admitida." if fuera else
                         f"Los impuestos no equivalen al {t * 100:.0f} % del subtotal ni a otra tasa admitida."),
                        cifras=_cifras(esperado, impuestos), campos=["impuestos"], evidencia=ev, evidencia_detalle=det)

    r = acc.evaluar("R-014")
    if subtotal is not None and impuestos is not None and total is not None:
        esperado = subtotal + impuestos - retenciones
        if not _cuadra(esperado, total, r.parametros["tolerancia"]):
            ev, det = _evidencia(f, "total")
            texto = "La suma de subtotal e impuestos" + (" menos retenciones" if retenciones else "")
            acc.agregar("R-014", "El total no coincide con subtotal más impuestos",
                        f"{texto} da un valor distinto al total impreso en la factura.",
                        cifras=_cifras(esperado, total), campos=["total"], evidencia=ev, evidencia_detalle=det)

    r = acc.evaluar("R-015")
    rfc_e, folio = n.rfc_normalizado(valor("emisor_rfc")), (valor("folio") or "").strip().upper()
    otros = [a for a in ctx.antecedentes if a.caso_id != caso_id]
    mismo_archivo = next((a for a in otros if ctx.sha256 and a.sha256 == ctx.sha256), None)
    mismo_folio = next((a for a in otros if rfc_e and folio and n.rfc_normalizado(a.emisor_rfc) == rfc_e
                        and (a.folio or "").strip().upper() == folio), None)
    if mismo_archivo:
        acc.agregar("R-015", "Factura duplicada", f"El archivo es idéntico al del caso {mismo_archivo.caso_id}.",
                    evidencia=f"caso {mismo_archivo.caso_id}", evidencia_detalle={"caso_anterior": mismo_archivo.caso_id})
    elif mismo_folio:
        acc.agregar("R-015", "Posible factura duplicada",
                    f"El caso {mismo_folio.caso_id} ya tiene una factura del mismo emisor con el folio {folio}, "
                    "pero el archivo es distinto. Puede ser una reexpedición.",
                    efecto=r.parametros.get("efecto_mismo_folio", "revision"), campos=["emisor_rfc", "folio"],
                    evidencia=f"caso {mismo_folio.caso_id}", evidencia_detalle={"caso_anterior": mismo_folio.caso_id})

    if ctx.proveedores_activos is not None and rfc_e and n.rfc_valido(rfc_e):
        acc.evaluar("R-017")
        if rfc_e not in ctx.proveedores_activos:
            ev, det = _evidencia(f, "emisor_rfc")
            acc.agregar("R-017", "El proveedor no está en el padrón",
                        f"El RFC {rfc_e} no aparece activo en el padrón de proveedores. Compras debe validarlo.",
                        campos=["emisor_rfc"], evidencia=ev, evidencia_detalle=det)

    rfc_r = n.rfc_normalizado(valor("receptor_rfc"))
    if ctx.entidades_receptoras is not None and rfc_r and n.rfc_valido(rfc_r):
        acc.evaluar("R-018")
        if rfc_r not in ctx.entidades_receptoras:
            ev, det = _evidencia(f, "receptor_rfc")
            acc.agregar("R-018", "La factura no está dirigida a una entidad del grupo",
                        f"El RFC del receptor {rfc_r} no corresponde a ninguna entidad receptora autorizada.",
                        campos=["receptor_rfc"], evidencia=ev, evidencia_detalle=det)

    r = acc.evaluar("R-021")
    if total is not None:
        tc = Decimal(str(g.get("tipo_cambio_usd_mxn", 18.5)))
        en_mxn = total * tc if moneda == "USD" else total
        limite = Decimal(str(r.parametros["monto_mxn"]))
        if moneda in ("MXN", "USD", "") and en_mxn >= limite:
            ev, det = _evidencia(f, "total")
            extra = f" (≈ {n.formato_monto(en_mxn)} MXN)" if moneda == "USD" else ""
            acc.agregar("R-021", "El monto requiere revisión de supervisión",
                        f"El total de {n.formato_monto(total)} {moneda or ''}{extra} es igual o mayor a "
                        f"{n.formato_monto(limite)} MXN.".replace("  ", " "),
                        campos=["total"], evidencia=ev, evidencia_detalle=det)

    return acc.resultado("Todos los campos se leyeron con buena confianza y las reglas evaluadas se cumplen.")


def _mapear_columnas(columnas: Iterable[str], alias: dict[str, list[str]]) -> tuple[dict[str, str], list[str]]:
    normal = {n.encabezado(c): c for c in columnas}
    mapa, faltan = {}, []
    for campo, opciones in alias.items():
        encontrada = next((normal[n.encabezado(o)] for o in opciones if n.encabezado(o) in normal), None)
        if encontrada is None:
            faltan.append(campo)
        else:
            mapa[campo] = encontrada
    return mapa, faltan


def _lista_filas(filas: list[int], maximo: int = 30) -> str:
    texto = ", ".join(map(str, filas[:maximo]))
    return texto + (f" y {len(filas) - maximo} más" if len(filas) > maximo else "")


def validar_registros(caso_id: str, t: TablaRegistros, ctx: Optional[Contexto] = None,
                      cat: Optional[Catalogo] = None) -> ResultadoValidacion:
    cat = cat or catalogo_por_defecto()
    ctx = ctx or Contexto()
    acc = _Acumulador(cat, caso_id)
    hoy = ctx.fecha_recepcion or date.today()
    total = len(t.filas)
    hoja = f"hoja «{t.hoja}», " if t.hoja else ""

    r = acc.evaluar("R-106")
    mapa, faltan = _mapear_columnas(t.columnas, r.parametros["alias"])
    if faltan:
        acc.agregar("R-106", "Faltan columnas obligatorias en el archivo",
                    f"El archivo no tiene las columnas: {', '.join(faltan)}.", campos=faltan,
                    evidencia=f"{hoja}encabezados", evidencia_detalle={"columnas_encontradas": t.columnas})

    def col(campo):
        return [(i + 1, fila.get(mapa[campo])) for i, fila in enumerate(t.filas)] if campo in mapa else []

    r = acc.evaluar("R-101")
    for campo in r.parametros["campos"]:
        if campo not in mapa:
            continue
        filas = [i for i, v in col(campo) if n.vacio(v)]
        if filas:
            acc.agregar("R-101", f"Campo obligatorio faltante: {campo}",
                        f"{len(filas)} de {total} registros no tienen {campo}. La política exige este campo para todo cliente dado de alta.",
                        cifras=[("Filas afectadas", _lista_filas(filas))], campos=[campo], filas=filas,
                        evidencia=f"columna {mapa[campo]}", evidencia_detalle={"columna": mapa[campo], "filas": filas})

    acc.evaluar("R-102")
    filas = [i for i, v in col("correo_contacto") if not n.vacio(v) and not n.correo_valido(v)]
    if filas:
        acc.agregar("R-102", "Correo de contacto con formato inválido",
                    f"{len(filas)} de {total} registros tienen un correo que no cumple el formato usuario@dominio.ext.",
                    cifras=[("Filas afectadas", _lista_filas(filas))], campos=["correo_contacto"], filas=filas,
                    evidencia=f"columna {mapa['correo_contacto']}", evidencia_detalle={"columna": mapa["correo_contacto"], "filas": filas})

    acc.evaluar("R-103")
    filas = [i for i, v in col("rfc") if not n.vacio(v) and not n.rfc_valido(v)]
    if filas:
        acc.agregar("R-103", "RFC con formato inválido",
                    f"{len(filas)} de {total} registros tienen un RFC que no cumple la estructura de la política P-011.",
                    cifras=[("Filas afectadas", _lista_filas(filas))], campos=["rfc"], filas=filas,
                    evidencia=f"columna {mapa['rfc']}", evidencia_detalle={"columna": mapa["rfc"], "filas": filas})

    r = acc.evaluar("R-104")
    minima = date.fromisoformat(r.parametros["minima"])
    malas, futuras, antiguas = [], [], []
    for i, v in col("alta"):
        if n.vacio(v):
            continue
        d = n.fecha_estricta_ddmmaaaa(v)
        if d is None:
            malas.append(i)
        elif d > hoy:
            futuras.append(i)
        elif d < minima:
            antiguas.append(i)
    for filas, titulo, texto in (
        (malas, "Fecha de alta con formato inválido", "no tienen una fecha en formato DD/MM/AAAA o no es una fecha que exista"),
        (futuras, "Fecha de alta futura", f"tienen una fecha de alta posterior al {hoy:%d/%m/%Y}"),
        (antiguas, "Fecha de alta anterior al inicio del sistema", f"tienen una fecha de alta anterior al {minima:%d/%m/%Y}"),
    ):
        if filas:
            acc.agregar("R-104", titulo, f"{len(filas)} de {total} registros {texto}.",
                        cifras=[("Filas afectadas", _lista_filas(filas))], campos=["alta"], filas=filas,
                        evidencia=f"columna {mapa['alta']}", evidencia_detalle={"columna": mapa["alta"], "filas": filas})

    acc.evaluar("R-105")
    vistos = defaultdict(list)
    for i, v in col("id_cliente"):
        if not n.vacio(v):
            vistos[str(v).strip().upper()].append(i)
    repetidos = {k: v for k, v in vistos.items() if len(v) > 1}
    if repetidos:
        filas = sorted(i for v in repetidos.values() for i in v)
        acc.agregar("R-105", "Identificadores de cliente repetidos",
                    f"{len(repetidos)} id_cliente aparecen más de una vez ({len(filas)} filas en total).",
                    cifras=[(k, "filas " + ", ".join(map(str, v))) for k, v in list(repetidos.items())[:5]],
                    campos=["id_cliente"], filas=filas, evidencia=f"columna {mapa['id_cliente']}",
                    evidencia_detalle={"columna": mapa["id_cliente"], "repetidos": repetidos})

    return acc.resultado(f"Los {total} registros cumplen las políticas evaluadas.")
