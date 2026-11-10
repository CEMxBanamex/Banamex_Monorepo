---
id: P-018
nombre: Unicidad de identificadores de cliente
tipo: gobernanza
version: "1.0"
historia: 2
area_responsable: Gobierno de Datos
vigente_desde: 2026-03-01
vigente_hasta: null
estado: vigente
---

# P-018 · Unicidad de identificadores de cliente

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Evitar que un mismo identificador represente a dos clientes distintos.

## 2. Unicidad

Ningún `id_cliente` puede aparecer más de una vez dentro del mismo archivo (regla **R-105 v1.0**). Si se repite, el hallazgo debe indicar el identificador y las filas en que aparece. El archivo no cumple la política.

## 3. Comparación

La comparación ignora espacios al inicio y al final y no distingue mayúsculas de minúsculas.
