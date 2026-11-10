"""Carga de los datos de negocio sintéticos (scripts/generar_negocio.py) en la base."""
import csv
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import CARPETA_SINTETICOS
from .contratos import Antecedente, CampoLeido, ConceptoLeido, FacturaExtraida
from .db.models import (
    Caso, CentroCosto, Cliente, EntidadReceptora, EventoBitacora, OrdenCompra, Pago, Proveedor, UsuarioEntidad,
)
from .persistencia import guardar_extraccion, guardar_resultado
from .reglas import normalizar as n
from .reglas.motor import Contexto, validar_factura

MX = ZoneInfo("America/Mexico_City")
FECHA_CORTE = date(2026, 11, 2)
CARPETA = CARPETA_SINTETICOS / "negocio"
NOMBRES = {"dev-ana": "Ana López", "dev-luis": "Luis Ortega", "dev-diego": "Diego Ruiz", "dev-admin": "Administrador Demo"}


def _csv(nombre: str) -> list[dict]:
    with open(CARPETA / nombre, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cargar_negocio(s: Session) -> dict:
    for r in _csv("proveedores_detalle.csv"):
        p = s.get(Proveedor, r["rfc"])
        if p:
            p.categoria, p.correo_contacto, p.plazo_pago_dias = r["categoria"], r["correo_contacto"], int(r["plazo_pago_dias"])
    for r in _csv("centros_costo.csv"):
        s.merge(CentroCosto(id=r["id"], nombre=r["nombre"], area=r["area"], entidad_rfc=r["entidad_rfc"],
                            responsable=r["responsable"], presupuesto_anual=Decimal(r["presupuesto_anual"])))
    for r in _csv("usuarios_entidades.csv"):
        if r["entidad_rfc"]:
            s.merge(UsuarioEntidad(usuario_id=r["usuario_id"], entidad_rfc=r["entidad_rfc"]))
    s.flush()
    ordenes = {}
    for r in _csv("ordenes_compra.csv"):
        oc = OrdenCompra(id=r["id"], proveedor_rfc=r["proveedor_rfc"], entidad_rfc=r["entidad_rfc"], centro_costo_id=r["centro_costo_id"],
                         fecha=date.fromisoformat(r["fecha"]), descripcion=r["descripcion"], moneda=r["moneda"],
                         monto=Decimal(r["monto"]), estado=r["estado"])
        s.add(oc)
        ordenes[oc.id] = oc
    for r in _csv("clientes.csv"):
        s.add(Cliente(id_cliente=r["id_cliente"], nombre=r["nombre"], tipo_persona=r["tipo_persona"], rfc=r["rfc"] or None,
                      correo_contacto=r["correo_contacto"] or None, segmento=r["segmento"], entidad_rfc=r["entidad_rfc"],
                      alta=date.fromisoformat(r["alta"]) if r["alta"] else None, activo=r["activo"] == "true"))
    s.flush()

    proveedores = set(s.scalars(select(Proveedor.rfc).where(Proveedor.activo.is_(True))))
    entidades = set(s.scalars(select(EntidadReceptora.rfc)))
    antecedentes: list[Antecedente] = []
    resumen = {"aceptado": 0, "rechazado": 0, "humana": 0}
    with open(CARPETA / "facturas_negocio.jsonl", encoding="utf-8") as fh:
        filas = [json.loads(linea) for linea in fh if linea.strip()]
    for d in filas:
        recibida = datetime.fromisoformat(d["recibida_en"]).replace(tzinfo=MX)
        revisada = datetime.fromisoformat(d["revisada_en"]).replace(tzinfo=MX) if d["revisada_en"] else None
        caso = Caso(id=d["caso_id"], tipo="factura", estado="procesando", origen="negocio", responsable_id=d["responsable"],
                    responsable_nombre=NOMBRES[d["responsable"]], creado_en=recibida)
        s.add(caso)
        s.flush()
        f = FacturaExtraida(
            campos={k: CampoLeido(valor=v, confianza=d["confianza"].get(k, 97)) for k, v in d["campos"].items() if v is not None},
            conceptos=[ConceptoLeido(**c) for c in d["conceptos"]], modelo="negocio-sintetico")
        r = validar_factura(caso.id, f, Contexto(proveedores_activos=proveedores, entidades_receptoras=entidades,
                                                 antecedentes=antecedentes, fecha_recepcion=recibida.date()))
        fac = guardar_extraccion(s, caso.id, f, cuando=recibida + timedelta(minutes=1), registrar_evento=False)
        fac.orden_compra_id = d["orden_compra_id"]
        guardar_resultado(s, r, cuando=recibida + timedelta(minutes=2))
        antecedentes.append(Antecedente(caso_id=caso.id, emisor_rfc=d["campos"]["emisor_rfc"], folio=d["campos"]["folio"], sha256=None))
        resumen[r.resultado_sugerido] += 1

        if revisada:
            final = d["decision_humana"] if r.resultado_sugerido == "humana" else r.resultado_sugerido
            caso.estado, caso.resultado_final, caso.revisado_por, caso.revisado_en = "revisado", final, NOMBRES[d["responsable"]], revisada
            s.add(EventoBitacora(caso_id=caso.id, fecha=revisada, actor_tipo="usuario", actor_id=d["responsable"],
                                 actor_nombre=NOMBRES[d["responsable"]], accion="confirmacion", tono="exito" if final == "aceptado" else "error",
                                 detalle=f"Resultado final: {final.capitalize()}"))
            oc = ordenes.get(d["orden_compra_id"])
            if final == "aceptado":
                emision = n.fecha(d["campos"]["fecha"])
                programada = emision + timedelta(days=d["plazo_pago_dias"])
                pago_real = programada + timedelta(days=d["pago_atraso_dias"])
                monto = fac.total if not d["pago_difiere"] else (fac.total * Decimal("0.98")).quantize(Decimal("0.01"))
                s.add(Pago(caso_id=caso.id, fecha_programada=programada, moneda=fac.moneda, monto=monto,
                           fecha_pago=pago_real if pago_real <= FECHA_CORTE else None,
                           estado="pagado" if pago_real <= FECHA_CORTE else "programado"))
            elif oc is not None:
                oc.estado = "abierta"
    s.flush()
    return {"facturas": len(filas), "ordenes_compra": len(ordenes), **resumen}
