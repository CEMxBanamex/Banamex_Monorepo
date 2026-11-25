"""Revisión experimental sin borrar lecturas; no genera decisiones de negocio."""
import argparse
import json
from pathlib import Path
import re

from steward_datos.contratos import CAMPOS_FACTURA, FacturaExtraida
from steward_datos.reglas import normalizar

from .extraccion import _filtrar_evidencia, _texto


def revisar_evidencia(factura: FacturaExtraida) -> dict:
    """Mantiene los valores originales separados de su respaldo textual.

    La coincidencia textual no verifica la imagen ni la asociación entre etiqueta,
    valor y rol. El informe no es una FacturaExtraida validada para las reglas.
    """
    if factura.origen_extraccion == "xml_cfdi":
        alertas = ["Lectura de atributos XML; no valida XSD, sellos, autenticidad ni estatus ante el SAT."]
        if not factura.uuid_fiscal:
            alertas.append("El XML no contiene UUID del timbre; no se considera un comprobante timbrado verificado.")
        if "cfdi:Comprobante/@Descuento =" in (factura.texto_completo or ""):
            alertas.append("El XML declara Descuento; las reglas actuales no modelan descuentos, revisar el cálculo del total.")
        return {
            "version": "lectura-cfdi-4.0-v1", "origen_extraccion": "xml_cfdi",
            "requiere_revision_humana": True, "habilitado_para_decision_automatica": False,
            "alcance": "Atributos copiados del XML recibido. No acredita validez fiscal ni consulta el SAT.",
            "uuid_fiscal": factura.uuid_fiscal, "alertas_documento": alertas,
            "campos": {nombre: {
                "valor_leido": campo.valor, "etiqueta_leida": campo.etiqueta,
                "estado": "atributo_xml" if campo.valor is not None else "sin_valor_leido",
                "motivos": [] if campo.valor is not None else ["No hay un atributo compatible explícito; no se infiere su valor."],
            } for nombre, campo in factura.campos.items()},
            "conceptos_leidos": [c.model_dump(mode="json") for c in factura.conceptos],
            "conceptos_verificados": False, "texto_completo": factura.texto_completo,
        }
    filtrada = factura.model_copy(deep=True)
    _filtrar_evidencia(filtrada)
    transcripcion = _texto(factura.texto_completo or "")
    campos = {}
    for nombre in CAMPOS_FACTURA:
        campo = factura.campos.get(nombre)
        valor = campo.valor if campo else None
        etiqueta = campo.etiqueta if campo else None
        respaldo = filtrada.campos.get(nombre)
        motivos = []
        if valor is None or not valor.strip():
            estado = "sin_valor_leido"
            motivos.append("El modelo no entregó un valor; esto no demuestra ausencia en el documento.")
        else:
            if _texto(valor) not in transcripcion:
                motivos.append("El valor no aparece en la transcripción del modelo.")
            if etiqueta and _texto(etiqueta) not in transcripcion:
                motivos.append("La etiqueta entregada no aparece en la transcripción del modelo.")
            if respaldo is None or respaldo.valor is None:
                if not motivos:
                    motivos.append("No satisface las condiciones de respaldo del filtro anterior.")
            if nombre == "folio":
                if re.search(r"\br\W*f\W*c\b", etiqueta or "", re.IGNORECASE) or re.fullmatch(
                        r"[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}", normalizar.rfc_normalizado(valor)):
                    motivos.append("El supuesto folio parece un RFC o usa su etiqueta; comprobar su asignación.")
                if valor.lstrip().startswith("#"):
                    motivos.append("El folio incluye #; comprobar la identidad del folio al buscar duplicados.")
            if nombre == "retenciones":
                importe = normalizar.monto(valor)
                if importe is not None and importe < 0:
                    motivos.append("Retenciones tiene signo negativo; verificar su interpretación antes de calcular el total.")
            estado = "pendiente_revision" if motivos else "coincidencia_textual"
        campos[nombre] = {
            "valor_leido": valor,
            "etiqueta_leida": etiqueta,
            "valor_filtro_anterior": respaldo.valor if respaldo else None,
            "estado": estado,
            "motivos": motivos,
        }
    alertas_documento = []
    if re.search(r"\bnota\s+de\s+credito\b", transcripcion) and _texto(factura.tipo_documento) == "factura":
        alertas_documento.append("La transcripción menciona nota de crédito, pero el modelo clasificó factura. Revisar tipo de documento.")
    return {
        "version": "experimental-conservar-lectura-v1",
        "requiere_revision_humana": True,
        "habilitado_para_decision_automatica": False,
        "alcance": (
            "Informe de consistencia con otra salida del mismo modelo. No verifica la imagen, "
            "la asociación de etiquetas o roles, ni la exactitud de los conceptos. "
            "No sustituye las reglas ni debe usarse como factura aprobada."
        ),
        "campos": campos,
        "alertas_documento": alertas_documento,
        "conceptos_leidos": [c.model_dump(mode="json") for c in factura.conceptos],
        "conceptos_verificados": False,
        "texto_completo": factura.texto_completo,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnosticos", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    archivos = sorted(args.diagnosticos.glob("piloto_*.json"))
    if not archivos:
        parser.error("No se encontraron archivos piloto_*.json en la carpeta indicada.")
    # Carpeta nueva: nunca sobrescribir diagnósticos ni informes anteriores.
    args.salida.mkdir(parents=True, exist_ok=False)
    for archivo in archivos:
        datos = json.loads(archivo.read_text(encoding="utf-8-sig"))
        factura = FacturaExtraida.model_validate(datos["antes_filtro"])
        informe = revisar_evidencia(factura)
        informe["archivo_diagnostico"] = archivo.name
        informe["modelo_solicitado"] = datos.get("modelo_solicitado")
        (args.salida / archivo.name).write_text(
            json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n{archivo.name}")
        for nombre, campo in informe["campos"].items():
            if campo["estado"] == "pendiente_revision":
                print(f"  {nombre}: conservado={campo['valor_leido']!r} | PENDIENTE DE REVISION")
                for motivo in campo["motivos"]:
                    print(f"    {motivo}")
        print(f"  Conceptos conservados sin verificar: {len(informe['conceptos_leidos'])}")
    print(f"\nInformes para revisión humana: {args.salida.resolve()}")


if __name__ == "__main__":
    main()
