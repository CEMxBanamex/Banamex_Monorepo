---
id: P-007
nombre: Datos mínimos de clientes
version: "1.3"
historia: 2
area_responsable: Gobierno de Datos
vigente_desde: 2026-07-01
vigente_hasta: null
estado: vigente
---

# P-007 · Datos mínimos de clientes

> Documento sintético elaborado para el piloto académico del Data Steward Agéntico. No es una política real de ninguna institución.

## 1. Objetivo

Definir los datos que debe tener todo registro de cliente dado de alta y el formato de los archivos con que se entregan esos registros para validación.

## 2. Campos obligatorios

Todo cliente dado de alta debe tener los siguientes campos con valor (regla **R-101 v1.3**):

- `id_cliente`: identificador interno del cliente.
- `nombre`: nombre o razón social.
- `rfc`: RFC del cliente, con la estructura de la política P-011.
- `correo_contacto`: correo electrónico de contacto.
- `alta`: fecha de alta del cliente.

Si un registro no tiene alguno de estos campos, el archivo no cumple la política. El hallazgo debe indicar qué campo falta y en qué filas.

## 3. Formato de los datos de contacto

El correo de contacto debe tener la forma `usuario@dominio.ext`, sin espacios (regla **R-102 v1.0**).

## 4. Estructura del archivo

Los registros se entregan en Excel (.xlsx o .xls) o CSV, con una fila de encabezados y un registro por fila (regla **R-106 v1.0**). Se aceptan estos nombres de columna:

| Campo | Nombres aceptados |
|---|---|
| id_cliente | id_cliente, id, cliente_id, numero_cliente |
| nombre | nombre, razon_social, nombre_cliente |
| rfc | rfc, rfc_cliente |
| correo_contacto | correo_contacto, correo, email, e-mail |
| alta | alta, fecha_alta, fecha_de_alta |

Si falta una columna obligatoria, el archivo no cumple la política aunque los demás datos sean correctos.

## 5. Cambios respecto a la versión 1.2

- El correo de contacto pasa a ser obligatorio para todo cliente dado de alta.
