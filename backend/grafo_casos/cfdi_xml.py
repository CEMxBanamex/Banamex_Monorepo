"""Lectura determinista de atributos de CFDI 4.0; no certifica validez fiscal."""
from io import BytesIO
import re
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as XML
from defusedxml.common import DefusedXmlException
from steward_datos.contratos import CAMPOS_FACTURA, CampoLeido, ConceptoLeido, FacturaExtraida

from .extraccion import ErrorExtraccion

CFDI = "{http://www.sat.gob.mx/cfd/4}"
TFD = "{http://www.sat.gob.mx/TimbreFiscalDigital}"
MAX_BYTES = 15 * 1024 * 1024


def _uno(elemento, nombre):
    encontrados = [] if elemento is None else elemento.findall(nombre)
    if len(encontrados) > 1:
        raise ErrorExtraccion("El CFDI contiene nodos únicos repetidos; revisar el XML.")
    return encontrados[0] if encontrados else None


def _atributo(elemento, nombre):
    return (elemento.get(nombre, "").strip() or None) if elemento is not None else None


def _numero(valor):
    # No pasar formatos ambiguos al normalizador visual (p. ej. 1e3 -> 13).
    if valor is not None and not re.fullmatch(r"[0-9]{1,18}(?:\.[0-9]{1,6})?", valor):
        raise ErrorExtraccion("El XML contiene un importe, cantidad o tasa con formato decimal no admitido.")
    return valor


def extraer_cfdi(datos: bytes) -> FacturaExtraida:
    if not datos or len(datos) > MAX_BYTES:
        raise ErrorExtraccion("El XML debe contener entre 1 byte y 15 MiB.")
    try:
        profundidad = cantidad = 0
        lector = XML.iterparse(BytesIO(datos), events=("start", "end"),
                               forbid_dtd=True, forbid_entities=True, forbid_external=True)
        for evento, elemento in lector:
            if evento == "start":
                profundidad += 1
                cantidad += 1
                if profundidad > 64 or cantidad > 20_000:
                    raise ErrorExtraccion("El XML supera los límites de estructura (64 niveles / 20000 nodos).")
            else:
                profundidad -= 1
        raiz = lector.root
    except (ParseError, DefusedXmlException, ValueError) as exc:
        raise ErrorExtraccion("XML inválido o con DTD/entidades no permitidas.") from exc
    if raiz.tag != CFDI + "Comprobante" or raiz.get("Version") != "4.0":
        raise ErrorExtraccion("Se requiere un Comprobante CFDI 4.0 con el namespace oficial.")
    tipo = raiz.get("TipoDeComprobante")
    if tipo not in {"I", "E"}:
        raise ErrorExtraccion("Esta vía admite CFDI de ingreso (I) y egreso (E).")
    emisor = _uno(raiz, CFDI + "Emisor")
    receptor = _uno(raiz, CFDI + "Receptor")
    conceptos = _uno(raiz, CFDI + "Conceptos")
    if emisor is None or receptor is None or conceptos is None:
        raise ErrorExtraccion("El CFDI requiere nodos Emisor, Receptor y Conceptos.")
    impuestos = _uno(raiz, CFDI + "Impuestos")
    complemento = _uno(raiz, CFDI + "Complemento")
    timbre = _uno(complemento, TFD + "TimbreFiscalDigital")
    identificador = _atributo(timbre, "UUID")
    if identificador and not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", identificador):
        raise ErrorExtraccion("El UUID del timbre no tiene un formato válido.")
    campos = {nombre: CampoLeido(pagina=None) for nombre in CAMPOS_FACTURA}

    def copiar(nombre, nodo, atributo, ruta):
        valor = _atributo(nodo, atributo)
        if nombre in {"subtotal", "total", "impuestos", "retenciones"}:
            valor = _numero(valor)
        campos[nombre] = CampoLeido(valor=valor, etiqueta=f"{ruta}/@{atributo}", pagina=None)

    for nombre, atributo in {"folio": "Folio", "fecha": "Fecha", "moneda": "Moneda", "subtotal": "SubTotal",
                             "total": "Total", "condiciones_pago": "CondicionesDePago"}.items():
        copiar(nombre, raiz, atributo, "cfdi:Comprobante")
    for rol, nodo, ruta in [("emisor", emisor, "cfdi:Comprobante/cfdi:Emisor"),
                            ("receptor", receptor, "cfdi:Comprobante/cfdi:Receptor")]:
        copiar(f"{rol}_nombre", nodo, "Nombre", ruta)
        copiar(f"{rol}_rfc", nodo, "Rfc", ruta)
    # Solo totales explícitos: no sumar impuestos de partidas ni inferir ceros.
    copiar("impuestos", impuestos, "TotalImpuestosTrasladados", "cfdi:Comprobante/cfdi:Impuestos")
    copiar("retenciones", impuestos, "TotalImpuestosRetenidos", "cfdi:Comprobante/cfdi:Impuestos")
    traslados = _uno(impuestos, CFDI + "Traslados")
    tasas = {_atributo(t, "TasaOCuota") for t in ([] if traslados is None else traslados.findall(CFDI + "Traslado"))
             if t.get("Impuesto") == "002" and t.get("TipoFactor") == "Tasa"}
    if len(tasas) == 1 and None not in tasas:
        campos["tasa_iva"] = CampoLeido(valor=_numero(next(iter(tasas))), pagina=None,
                                       etiqueta="cfdi:Comprobante/cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado/@TasaOCuota")
    partidas = []
    for concepto in conceptos.findall(CFDI + "Concepto"):
        descripcion = _atributo(concepto, "Descripcion")
        if not descripcion:
            raise ErrorExtraccion("Un concepto no contiene Descripcion; revisar el XML.")
        partidas.append(ConceptoLeido(descripcion=descripcion, cantidad=_numero(_atributo(concepto, "Cantidad")),
                                     precio_unitario=_numero(_atributo(concepto, "ValorUnitario")),
                                     importe=_numero(_atributo(concepto, "Importe"))))
    if not partidas:
        raise ErrorExtraccion("El CFDI no contiene conceptos.")
    # Representación de los datos analizados, no una transcripción visual ni un XSD.
    lineas = []

    def nombre(tag):
        return tag.replace(CFDI, "cfdi:").replace(TFD, "tfd:")

    def recorrer(nodo, ruta):
        for atributo, valor in nodo.attrib.items():
            lineas.append(f"{ruta}/@{nombre(atributo)} = {valor}")
        if nodo.text and nodo.text.strip():
            lineas.append(f"{ruta}/text() = {nodo.text.strip()}")
        for hijo in nodo:
            recorrer(hijo, ruta + "/" + nombre(hijo.tag))

    recorrer(raiz, "cfdi:Comprobante")
    return FacturaExtraida(tipo_documento="factura" if tipo == "I" else "nota_credito", campos=campos,
                          conceptos=partidas, texto_completo="\n".join(lineas), modelo=None, paginas=0,
                          origen_extraccion="xml_cfdi", uuid_fiscal=identificador)
