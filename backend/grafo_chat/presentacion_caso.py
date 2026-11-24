"""Presentación legible del detalle de un caso, sin inferir decisiones."""

import json


def formatear_caso(resultado):
    datos = getattr(resultado, "structuredContent", None)
    if datos is None:
        datos = getattr(resultado, "structured_content", None)
    if datos is None:
        for bloque in getattr(resultado, "content", None) or []:
            try:
                datos = json.loads(getattr(bloque, "text", ""))
                break
            except (ValueError, TypeError):
                continue
    if not isinstance(datos, dict) or not datos.get("id"):
        return None
    estados = {"revision": "En revisión", "revisado": "Revisado", "procesando": "Procesando", "error": "Error"}
    resultados = {"humana": "Requiere revisión humana", "aceptado": "Aceptado", "rechazado": "Rechazado"}
    lineas = [
        f"Caso {datos['id']}",
        f"Archivo: {datos.get('archivo') or 'No disponible'}",
        f"Estado: {estados.get(datos.get('estado'), datos.get('estado') or 'No disponible')}",
        f"Resultado sugerido: {resultados.get(datos.get('resultado_sugerido'), datos.get('resultado_sugerido') or 'No disponible')}",
        f"Decisión final: {resultados.get(datos.get('resultado_final'), datos.get('resultado_final') or 'Pendiente')}",
        "", str(datos.get("explicacion") or "Sin explicación registrada."),
        "", "Hallazgos y evidencia",
    ]
    for h in datos.get("hallazgos") or []:
        lineas.extend([
            f"• {h.get('regla_id', 'Sin regla')} · {h.get('titulo', 'Hallazgo')}",
            str(h.get("texto") or ""),
            f"Evidencia: {h.get('evidencia') or 'No registrada'}",
        ])
        for cifra in h.get("cifras") or []:
            if isinstance(cifra, (list, tuple)) and len(cifra) == 2:
                lineas.append(f"{cifra[0]}: {cifra[1]}")
        lineas.append("")
    eventos = datos.get("eventos") or []
    if eventos:
        lineas.append("Actividad registrada")
        for e in eventos[:10]:
            lineas.append(f"• {e.get('actor') or 'Sin actor'}: {e.get('detalle') or e.get('accion') or 'Evento'}")
    return "\n".join(lineas)
