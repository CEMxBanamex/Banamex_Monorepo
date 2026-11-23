"""Agente Redactor de Hallazgos (Paso 3 de 3 del Grafo de Casos).

Dueño: Yael.
Transforma los hallazgos técnicos del validador en una justificación humana
clara, registra cada hallazgo en la bitácora de auditoría y prepara el estado
para la pausa (interrupt) de revisión del analista.
"""
from typing import Optional

from steward_datos.contratos import (
    HallazgoOut,
    RegistrarHallazgoEntrada,
    Resultado,
)


def redactar_explicacion_caso(
    caso_id: str,
    resultado_sugerido: Resultado,
    motivo: str,
    hallazgos: Optional[list[dict]] = None,
) -> tuple[str, list[dict]]:
    """Genera la explicación institucional del caso y formatea cada hallazgo.

    Sigue las directrices del System Prompt en datos/agentes/redactor.md:
    - Recomienda, nunca autoriza ni decide.
    - Cita regla, versión, política y evidencia.
    - Desglosa cifras cuando existen diferencias cuantitativas.
    """
    hallazgos = hallazgos or []
    detalles_redactados = []

    if not hallazgos:
        if resultado_sugerido == "aceptado":
            explicacion = (
                f"La revisión automática del caso {caso_id} no detectó inconsistencias. "
                "Los montos e impuestos coinciden con las reglas vigentes. "
                "Se sugiere confirmar el resultado como Aceptado."
            )
        else:
            explicacion = f"{motivo} El analista debe registrar la decisión final."
        return explicacion, detalles_redactados

    # Si hay hallazgos estructurados
    bloques_texto = []
    hay_hallazgo_sin_politica = False
    for h in hallazgos:
        regla = h.get("regla_id")
        version = h.get("regla_version")
        politica = h.get("politica_id")
        seccion = h.get("politica_seccion", "")
        titulo = h.get("titulo", "Discrepancia detectada")
        cifras = h.get("cifras", [])
        evidencia = h.get("evidencia", "documento")

        partes_cita = []
        if regla:
            partes_cita.append(f"Regla {regla}" + (f" v{version}" if version else ""))
        if politica:
            cita_pol = f"sustentada en {politica}"
            if seccion:
                cita_pol += f" ({seccion})"
            partes_cita.append(cita_pol)
        else:
            hay_hallazgo_sin_politica = True
            partes_cita.append("Sin política aplicable (requiere revisión humana)")

        cita_str = " · ".join(partes_cita)
        cifras_str = ""
        if cifras:
            cifras_formateadas = [f"{etiqueta}: {valor}" for etiqueta, valor in cifras]
            cifras_str = f" [{', '.join(cifras_formateadas)}]"

        texto_hallazgo = (
            f"• {titulo}: {cita_str}. "
            f"Evidencia en {evidencia}.{cifras_str}"
        )
        bloques_texto.append(texto_hallazgo)

        detalles_redactados.append({
            "regla_id": regla or "",
            "regla_version": version or "",
            "politica_id": politica or "",
            "titulo": titulo,
            "cifras": cifras,
            "evidencia": evidencia,
        })

    resultado_final_sugerido = "humana" if hay_hallazgo_sin_politica else resultado_sugerido
    sintesis = (
        f"Se sugiere '{resultado_final_sugerido.upper()}' para el caso {caso_id} debido a los siguientes hallazgos:\n"
        + "\n".join(bloques_texto)
        + "\nEl analista de cuentas por pagar debe verificar las evidencias y registrar la decisión final."
    )
    return sintesis, detalles_redactados


def ejecutar_redactor(
    caso_id: str,
    resultado_sugerido: Resultado,
    motivo: str,
    hallazgos: Optional[list[dict]] = None,
    registrar_en_bd: bool = False,
    sesion_bd=None,
) -> dict:
    """Ejecuta el nodo Redactor de Hallazgos."""
    explicacion, redactados = redactar_explicacion_caso(
        caso_id=caso_id,
        resultado_sugerido=resultado_sugerido,
        motivo=motivo,
        hallazgos=hallazgos,
    )

    eventos_ids = []
    if registrar_en_bd and hallazgos:
        from steward_datos.tools.registrar_hallazgo import registrar_hallazgo

        for h in hallazgos:
            try:
                hallazgo_obj = HallazgoOut(
                    regla_id=h.get("regla_id", "R-014"),
                    regla_version=h.get("regla_version", "2.1"),
                    politica_id=h.get("politica_id", "P-002"),
                    efecto=h.get("efecto", "revision"),
                    severidad=h.get("severidad", "adv"),
                    titulo=h.get("titulo", "Hallazgo del redactor"),
                    texto=h.get("texto", explicacion),
                    cifras=h.get("cifras"),
                    evidencia=h.get("evidencia", "documento"),
                )
                res = registrar_hallazgo(
                    RegistrarHallazgoEntrada(
                        caso_id=caso_id,
                        hallazgo=hallazgo_obj,
                        origen="codigo",
                        actor_nombre="Agente Redactor",
                    ),
                    s=sesion_bd,
                )
                eventos_ids.append(res.evento_id)
            except Exception:
                # Si no está en BD o es prueba aislada, continuar
                pass

    return {
        "explicacion": explicacion,
        "hallazgos_redactados": redactados,
        "eventos_bitacora": eventos_ids,
    }
