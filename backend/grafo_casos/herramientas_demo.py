"""Herramientas deterministas para demostrar el flujo de una factura."""
from decimal import Decimal, InvalidOperation

from steward_datos.contratos import CampoLeido, FacturaExtraida, Resultado


CAMPOS_MONTO = ("subtotal", "impuestos", "total")


def extraer_factura_demo() -> FacturaExtraida:
    """Devuelve una factura fija para probar el flujo sin servicios externos."""
    return FacturaExtraida(campos={
        "folio": CampoLeido(valor="DEMO-028"),
        "moneda": CampoLeido(valor="MXN"),
        "subtotal": CampoLeido(valor="100.00"),
        "impuestos": CampoLeido(valor="16.00"),
        "total": CampoLeido(valor="120.00"),
    })


def validar_factura_demo(
    factura: FacturaExtraida,
) -> tuple[Resultado, str]:
    """Compara subtotal + impuestos contra total.

    Los datos incompletos o con importes inválidos generan ValueError.
    Una diferencia aritmética válida se deriva a revisión humana.
    """
    def monto(campo: str) -> Decimal:
        dato = factura.campos.get(campo)

        if dato is None or dato.valor is None:
            raise ValueError(f"Falta el campo obligatorio '{campo}'.")

        valor = str(dato.valor).strip()
        if not valor:
            raise ValueError(f"El campo '{campo}' está vacío.")

        try:
            importe = Decimal(valor)
        except InvalidOperation as exc:
            raise ValueError(
                f"El campo '{campo}' no contiene un importe válido."
            ) from exc

        if not importe.is_finite():
            raise ValueError(
                f"El campo '{campo}' debe contener un importe finito."
            )

        return importe

    importes = {campo: monto(campo) for campo in CAMPOS_MONTO}

    esperado = importes["subtotal"] + importes["impuestos"]
    total = importes["total"]

    if total != esperado:
        diferencia = abs(total - esperado)
        return "humana", (
            f"El total capturado es {total:.2f} MXN y el esperado es "
            f"{esperado:.2f} MXN; la diferencia es {diferencia:.2f} MXN."
        )

    return "aceptado", (
        "El total coincide con el subtotal más los impuestos."
    )


def redactar_demo(motivo: str) -> str:
    """Genera una explicación breve para el paso de revisión humana."""
    if not isinstance(motivo, str) or not motivo.strip():
        raise ValueError("El motivo de la revisión debe ser texto no vacío.")

    return f"{motivo.strip()} El analista debe registrar la decisión final."
