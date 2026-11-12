"""Herramientas simuladas para una factura de prueba."""
from decimal import Decimal

from steward_datos.contratos import CampoLeido, FacturaExtraida, Resultado


def extraer_factura_demo() -> FacturaExtraida:
    return FacturaExtraida(campos={
        "folio": CampoLeido(valor="DEMO-028"),
        "moneda": CampoLeido(valor="MXN"),
        "subtotal": CampoLeido(valor="100.00"),
        "impuestos": CampoLeido(valor="16.00"),
        "total": CampoLeido(valor="120.00"),
    })


def validar_factura_demo(factura: FacturaExtraida) -> tuple[Resultado, str]:
    def monto(campo: str) -> Decimal:
        valor = factura.campos[campo].valor
        if valor is None:
            raise ValueError(f"Falta el campo {campo} en la factura demo.")
        return Decimal(valor)

    esperado = monto("subtotal") + monto("impuestos")
    total = monto("total")
    if total != esperado:
        return "humana", (
            f"El total capturado es {total:.2f} MXN y el esperado es "
            f"{esperado:.2f} MXN; la diferencia es {abs(total - esperado):.2f} MXN."
        )
    return "aceptado", "El total coincide con el subtotal más los impuestos."


def redactar_demo(motivo: str) -> str:
    return f"{motivo} El analista debe registrar la decisión final."
