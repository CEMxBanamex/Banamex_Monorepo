"""Presentación de eventos de auditoría sin inferir decisiones."""

import json


def formatear_bitacora(resultado):
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
    if not isinstance(datos, dict) or not isinstance(datos.get("eventos"), list):
        raise ValueError("La bitácora devolvió un formato inesperado")
    lineas = ["Bitácora consultada", f"Eventos disponibles: {datos.get('total', len(datos['eventos']))}"]
    if not datos["eventos"]:
        lineas.append("No se encontraron eventos disponibles para esta consulta.")
    for evento in datos["eventos"]:
        regla = f" · {evento['regla']}" if evento.get("regla") else ""
        lineas.append(
            f"• {evento.get('fecha') or 'Sin fecha'} · "
            f"{evento.get('actor_nombre') or 'Sin actor'}{regla}: "
            f"{evento.get('detalle') or evento.get('accion') or 'Evento'}"
        )
    return "\n".join(lineas)
