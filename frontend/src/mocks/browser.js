import { setupWorker } from 'msw/browser'
import { http, HttpResponse } from 'msw'
import { handlers } from './handlers.js'

const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// Chat simulado (sin VITE_CHAT_REAL). Los de casos y bitácora vienen de handlers.js.
const handlersChat = [
  http.post('/api/chat/stream', async ({ request }) => {
    const entrada = await request.json()

    if (
      typeof entrada.mensaje !== 'string' ||
      !entrada.mensaje.trim() ||
      entrada.mensaje.trim().length > 2000
    ) {
      return HttpResponse.json(
        { detail: 'Escribe un mensaje de entre 1 y 2000 caracteres.' },
        { status: 422 },
      )
    }

    const encoder = new TextEncoder()
    const inicio = performance.now()
    let cancelado = false

    const stream = new ReadableStream({
      async start(controller) {
        function emitir(nombre, datos) {
          if (!cancelado) {
            controller.enqueue(
              encoder.encode(
                `event: ${nombre}\ndata: ${JSON.stringify(datos)}\n\n`,
              ),
            )
          }
        }

        emitir('paso', {
          id: 'demo-1',
          texto: 'Preparando consulta de ejemplo',
          detalle: 'Simulación para probar la interfaz.',
          estado: 'en_curso',
        })

        await esperar(700)
        if (cancelado) return

        emitir('paso', {
          id: 'demo-1',
          texto: 'Preparando consulta de ejemplo',
          detalle: 'Entrada de ejemplo preparada.',
          estado: 'completado',
        })

        emitir('paso', {
          id: 'demo-2',
          texto: 'Preparando respuesta de ejemplo',
          detalle: 'No se están consultando herramientas reales.',
          estado: 'en_curso',
        })

        await esperar(700)
        if (cancelado) return

        if (entrada.mensaje.trim().toLowerCase() === 'error') {
          emitir('paso', {
            id: 'demo-2',
            texto: 'Preparando respuesta de ejemplo',
            detalle: 'Fallo simulado para comprobar la recuperación.',
            estado: 'error',
          })

          controller.close()
          return
        }

        emitir('paso', {
          id: 'demo-2',
          texto: 'Preparando respuesta de ejemplo',
          detalle: 'Respuesta ficticia preparada.',
          estado: 'completado',
        })

        emitir('respuesta', {
          respuesta: entrada.caso_id
            ? `Ejemplo asociado al caso ${entrada.caso_id}. Todavía no se han consultado sus datos ni sus políticas.`
            : 'Esta es una respuesta simulada del Asistente. La conexión con las herramientas y el modelo de IA se realizará después.',
          caso_id: entrada.caso_id ?? null,
          simulado: true,
          tipo: 'informacion_general',
          fuentes: entrada.mensaje.trim().toLowerCase() === 'fuentes'
            ? ['Fuente ficticia para probar la pantalla, sin respaldo documental real.']
            : [],
          duracion_ms: Math.round(performance.now() - inicio),
        })

        controller.close()
      },

      cancel() {
        cancelado = true
      },
    })

    return new HttpResponse(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
    })
  }),
]

export const worker = setupWorker(...handlers, ...handlersChat)