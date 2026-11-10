---
id: P-022
nombre: Calidad de datos
tipo: gobernanza
version: "1.0"
historia: null
area_responsable: Oficina de Gobierno de Datos
vigente_desde: 2026-03-01
vigente_hasta: null
estado: vigente
---

# P-022 · Calidad de datos

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Definir cómo se mide la calidad de los datos, qué umbrales se exigen y qué se hace cuando no se cumplen.

## 2. Dimensiones de calidad

- **Completitud:** el dato obligatorio está presente.
- **Unicidad:** el registro no está duplicado según su llave de negocio.
- **Validez:** el valor cumple su formato o rango (por ejemplo, la estructura del RFC de P-011).
- **Consistencia:** el dato coincide con otros datos relacionados (por ejemplo, total = subtotal + impuestos).
- **Oportunidad:** el registro se procesó dentro del plazo esperado.

## 3. Reglas de calidad y umbrales

Cada regla de calidad mide una dimensión sobre una tabla y tiene un umbral mínimo de cumplimiento. Las reglas vigentes del piloto son:

- Facturas: RFC del emisor y folio completos (99 %), folio único por emisor (99.5 %), total consistente (98 %) y revisión en 48 horas o menos (90 %).
- Proveedores: RFC válido (100 %).
- Clientes: correo completo (99 %) y válido (99.5 %), RFC válido (99.5 %), identificador único (100 %) y fecha de alta completa (99.5 %).
- Órdenes de compra: centro de costo completo (100 %).
- Pagos: pagados a más tardar en su fecha programada (90 %).

## 4. Ejecución

Las reglas se ejecutan cada semana y su resultado (porcentaje que cumple) queda registrado con su fecha. En el piloto los resultados se precalculan al cargar los datos.

## 5. Incumplimiento

Si una regla queda por debajo de su umbral, el data steward del dominio (P-021) abre un incidente, identifica los registros que fallan y propone la corrección al data owner. Una regla que falla dos semanas seguidas se reporta a la Oficina de Gobierno de Datos.
