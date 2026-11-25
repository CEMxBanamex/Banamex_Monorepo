import { http, HttpResponse } from 'msw'
import { CASOS, CAMPOS_FACTURA, HALLAZGOS_FACTURA, EVENTOS } from '../data.js'

let casos = [...CASOS]
let eventos = [...EVENTOS]

export const handlers = [
  // GET /api/casos
  http.get('/api/casos', ({ request }) => {
    const url = new URL(request.url)
    const tipo = url.searchParams.get('tipo')
    const estado = url.searchParams.get('estado')

    let filtrados = casos
    if (tipo) filtrados = filtrados.filter((c) => c.tipo === tipo)
    if (estado) filtrados = filtrados.filter((c) => c.estado === estado)

    return HttpResponse.json({
      casos: filtrados,
      metricas: {
        total: casos.length,
        en_revision: casos.filter((c) => c.estado === 'revision').length,
        revisados: casos.filter((c) => c.estado === 'revisado').length,
        procesando: casos.filter((c) => c.estado === 'procesando').length,
      },
    })
  }),

  // GET /api/casos/:id
  http.get('/api/casos/:id', ({ params }) => {
    const { id } = params
    const c = casos.find((caso) => caso.id.toLowerCase() === id.toLowerCase())
    if (!c) {
      return new HttpResponse(JSON.stringify({ detalle: `Caso ${id} no encontrado` }), { status: 404 })
    }

    return HttpResponse.json({
      ...c,
      resultado_sugerido: c.resultado,
      resultado_final: c.resultado,
      explicacion: 'Revisión automática de reglas contra documento y políticas.',
      campos: CAMPOS_FACTURA,
      hallazgos: HALLAZGOS_FACTURA,
      eventos: eventos.filter((e) => e.caso === c.id),
    })
  }),

  // POST /api/casos/url-subida
  http.post('/api/casos/url-subida', async ({ request }) => {
    const body = await request.json()
    const s3_key = `casos/${Date.now()}_${body.nombre_archivo}`
    return HttpResponse.json({
      upload_url: `https://s3.amazonaws.com/data-steward-mock/${s3_key}?signature=mock`,
      s3_key,
      expira_en_segundos: 900,
    })
  }),

  // POST /api/casos
  http.post('/api/casos', async ({ request }) => {
    const body = await request.json()
    const nuevoId = `F-104${casos.length + 1}`
    const nuevoCaso = {
      id: nuevoId,
      archivo: body.archivo || 'factura_nueva.pdf',
      tipo: body.tipo || 'Factura',
      estado: 'procesando',
      resultado: 'humana',
      fecha: 'Hoy',
      responsable: 'Ana López',
      variante: 'normal',
    }
    casos.unshift(nuevoCaso)
    return HttpResponse.json({
      id: nuevoId,
      estado: 'procesando',
      mensaje: `Caso ${nuevoId} creado con éxito.`,
    }, { status: 201 })
  }),

  // POST /api/casos/:id/decision
  http.post('/api/casos/:id/decision', async ({ params, request }) => {
    const { id } = params
    const body = await request.json()
    const eventoId = `EV-${Math.floor(3100 + Math.random() * 900)}`

    // Actualizar el estado del caso
    const casoIndex = casos.findIndex((c) => c.id.toLowerCase() === id.toLowerCase())
    if (casoIndex !== -1) {
      casos[casoIndex] = {
        ...casos[casoIndex],
        estado: 'revisado',
        resultado: body.resultado || (body.accion === 'confirmar' ? 'aceptado' : 'humana'),
      }
    }

    // Agregar evento a la bitácora
    const nuevoEvento = {
      id: eventoId,
      fecha: 'Hoy · Recién',
      caso: id.toUpperCase(),
      quien: 'Ana López',
      ini: 'AL',
      accion: body.accion === 'confirmar' ? 'Confirmación' : body.accion === 'corregir' ? 'Corrección de dato' : 'Escalamiento',
      tono: body.accion === 'confirmar' ? 'exito' : body.accion === 'corregir' ? 'adv' : 'error',
      detalle: body.comentario || `Decisión ${body.accion} registrada por analista.`,
      regla: null,
    }
    eventos.unshift(nuevoEvento)

    return HttpResponse.json({
      caso_id: id,
      estado: 'revisado',
      resultado_final: body.resultado || 'aceptado',
      evento_id: eventoId,
      mensaje: `Decisión ${body.accion} guardada en bitácora.`,
    })
  }),

  // GET /api/bitacora
  http.get('/api/bitacora', ({ request }) => {
    const url = new URL(request.url)
    const caso = url.searchParams.get('caso')
    const quien = url.searchParams.get('quien')
    const accion = url.searchParams.get('accion')

    let filtrados = eventos
    if (caso) filtrados = filtrados.filter((e) => e.caso.toLowerCase() === caso.toLowerCase())
    if (quien) filtrados = filtrados.filter((e) => e.quien.toLowerCase().includes(quien.toLowerCase()))
    if (accion) filtrados = filtrados.filter((e) => e.accion.toLowerCase().includes(accion.toLowerCase()))

    return HttpResponse.json({
      eventos: filtrados,
      total: filtrados.length,
      limite: 50,
      offset: 0,
      filtros: {
        casos: [...new Set(eventos.map((e) => e.caso))],
        acciones: [...new Set(eventos.map((e) => e.accion))],
        usuarios: [...new Set(eventos.map((e) => e.quien))],
      },
    })
  }),
]
