// Datos ficticios del prototipo. No hay conexión con ningún servicio.

export const USUARIOS = {
  ana: { nombre: 'Ana López', rol: 'Analista de cuentas por pagar', iniciales: 'AL' },
  diego: { nombre: 'Diego Ruiz', rol: 'Analista de datos', iniciales: 'DR' },
}

export const CASOS = [
  { id: 'F-1042', archivo: 'factura_1042.pdf', tipo: 'Factura', estado: 'revision', resultado: 'humana', fecha: '26 oct 2026', responsable: 'Ana López', variante: 'normal' },
  { id: 'F-1041', archivo: 'factura_1041.png', tipo: 'Factura', estado: 'revisado', resultado: 'aceptado', fecha: '26 oct 2026', responsable: 'Ana López', variante: 'sinHallazgos' },
  { id: 'F-1040', archivo: 'factura_1040.jpg', tipo: 'Factura', estado: 'revisado', resultado: 'rechazado', fecha: '25 oct 2026', responsable: 'Luis Ortega', variante: 'normal' },
  { id: 'V-0207', archivo: 'clientes_octubre.xlsx', tipo: 'Validación con políticas', estado: 'procesando', resultado: null, fecha: '26 oct 2026', responsable: 'Diego Ruiz' },
  { id: 'V-0206', archivo: 'registros_prueba.csv', tipo: 'Validación con políticas', estado: 'error', resultado: null, fecha: '25 oct 2026', responsable: 'Diego Ruiz', variante: 'error' },
]

export const CAMPOS_FACTURA = [
  { id: 'proveedor', etiqueta: 'Proveedor', valor: 'Proveedor Demo SA', conf: 98 },
  { id: 'fecha', etiqueta: 'Fecha', valor: '12/03/2026', conf: 62 },
  { id: 'subtotal', etiqueta: 'Subtotal', valor: '10,000.00', conf: 97 },
  { id: 'impuestos', etiqueta: 'Impuestos', valor: '1,600.00', conf: 96 },
  { id: 'total', etiqueta: 'Total', valor: '12,000.00', conf: 95 },
  { id: 'moneda', etiqueta: 'Moneda', valor: 'MXN', conf: 99 },
]

export const HALLAZGOS_FACTURA = [
  {
    id: 'total', tipo: 'adv',
    titulo: 'El total no coincide con subtotal más impuestos',
    texto: 'La suma de subtotal e impuestos da un valor distinto al total impreso en la factura.',
    cifras: [['Esperado', '11,600.00'], ['Encontrado', '12,000.00'], ['Diferencia', '400.00']],
    regla: 'R-014', version: '2.1', evidencia: 'página 1, total',
  },
  {
    id: 'fecha', tipo: 'info',
    titulo: 'La fecha se leyó con baja confianza',
    texto: 'El mes no es legible con claridad. Verifica la fecha contra el documento original.',
    regla: 'R-003', version: '1.0', evidencia: 'página 1, fecha',
  },
]

export const POLITICAS = [
  { id: 'P-007', nombre: 'Datos mínimos de clientes', version: '1.3', vigencia: '01/07/2026 – sin fecha de fin' },
  { id: 'P-011', nombre: 'Formato de RFC', version: '2.0', vigencia: '15/01/2026 – sin fecha de fin' },
  { id: 'P-015', nombre: 'Fechas de alta válidas', version: '1.1', vigencia: '01/03/2026 – 31/12/2026' },
]

const FALTANTES = [14, 27, 33, 48, 61, 79, 95, 112]
const VISIBLES = [11, 12, 13, 14, 15, 16, 17, '18 a 26', 27, 28, '29 a 32', 33, 34, 35, '36 a 47', 48, 49]
const ALTA = { 11: '03/10', 12: '03/10', 13: '04/10', 14: '04/10', 15: '05/10', 16: '05/10', 17: '06/10', 27: '08/10', 28: '08/10', 33: '09/10', 34: '09/10', 35: '10/10', 48: '12/10', 49: '12/10' }

export const REGISTROS = VISIBLES.map((n) =>
  typeof n === 'string'
    ? { salto: n }
    : {
        fila: n,
        id: `C-${String(n).padStart(5, '0')}`,
        nombre: `Cliente Ficticio ${n}`,
        rfc: 'XAXX010101000',
        correo: FALTANTES.includes(n) ? null : `contacto${n}@ejemplo.mx`,
        alta: ALTA[n],
      },
)
export const FILAS_FALTANTES = FALTANTES

export const EVENTOS = [
  { id: 'EV-3112', fecha: '26 oct 2026 · 11:58', caso: 'F-1041', quien: 'Ana López', ini: 'AL', accion: 'Confirmación', tono: 'exito', detalle: 'Confirmó el resultado sugerido: Aceptado', regla: null },
  {
    id: 'EV-3108', fecha: '26 oct 2026 · 11:42', caso: 'F-1042', quien: 'Ana López', ini: 'AL', accion: 'Corrección de dato', tono: 'adv', detalle: 'Campo fecha corregido', regla: 'R-003 · v1.0',
    extra: { texto: 'Se corrigió el campo fecha después de verificarlo contra el documento original (página 1).', antes: '12/03/2026', despues: '12/08/2026' },
  },
  { id: 'EV-3104', fecha: '26 oct 2026 · 10:15', caso: 'F-1042', quien: 'Agente', accion: 'Regla aplicada', tono: 'info', detalle: 'El total no coincide con subtotal más impuestos', regla: 'R-014 · v2.1' },
  { id: 'EV-3103', fecha: '26 oct 2026 · 10:15', caso: 'F-1042', quien: 'Agente', accion: 'Regla aplicada', tono: 'info', detalle: 'Fecha leída con baja confianza (62 %)', regla: 'R-003 · v1.0' },
  { id: 'EV-3102', fecha: '26 oct 2026 · 10:14', caso: 'F-1042', quien: 'Agente', accion: 'Extracción de datos', tono: 'info', detalle: '6 campos extraídos de factura_1042.pdf', regla: null },
  { id: 'EV-3087', fecha: '25 oct 2026 · 17:30', caso: 'F-1040', quien: 'Luis Ortega', ini: 'LO', accion: 'Escalamiento', tono: 'error', detalle: 'Caso escalado a supervisión', regla: 'R-021 · v1.2' },
  { id: 'EV-3079', fecha: '25 oct 2026 · 16:02', caso: 'V-0206', quien: 'Agente', accion: 'Error de procesamiento', tono: 'error', detalle: 'No se pudo leer registros_prueba.csv', regla: null },
]
