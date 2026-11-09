---
id: P-011
nombre: Formato de RFC
tipo: gobernanza
version: "2.0"
historia: null  # aplica a ambas historias
area_responsable: Gobierno de Datos
vigente_desde: 2026-01-15
vigente_hasta: null
estado: vigente
---

# P-011 · Formato de RFC

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución. Aplica a facturas (Historia 1) y a registros de clientes (Historia 2).

## 1. Objetivo

Asegurar que todo RFC capturado o leído tenga una estructura válida antes de usarse para identificar a un proveedor o a un cliente.

## 2. Estructura del RFC

Un RFC válido se escribe en mayúsculas, sin espacios ni guiones, y tiene una de estas dos formas (reglas **R-002 v2.0** para facturas y **R-103 v2.0** para registros):

- **Persona moral: 12 caracteres.** Tres letras (se admiten Ñ y &), seis dígitos de fecha en formato AAMMDD y tres caracteres alfanuméricos de homoclave.
- **Persona física: 13 caracteres.** Cuatro letras, seis dígitos de fecha en formato AAMMDD y tres caracteres alfanuméricos de homoclave.

Los seis dígitos deben formar una fecha que exista en el calendario. Por ejemplo, un RFC con fecha 230231 no es válido porque el 31 de febrero no existe.

## 3. RFC genéricos

Los RFC genéricos XAXX010101000 (público en general) y XEXX010101000 (extranjeros) tienen una estructura válida. Esta política no los prohíbe, pero otras políticas pueden restringir su uso.

## 4. Normalización

Antes de validar se eliminan espacios y guiones y se convierten las letras a mayúsculas. El valor original se conserva en la evidencia.
