import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import './Asistente.css'
import { Bot, ArrowUp, Square, Loader } from 'lucide-react'
import { identidadApi } from '../api.js'
import { CHAT_REAL, CHAT_API } from '../chatConfig.js'

const ESTADOS = {
  pendiente: 'Pendiente',
  en_curso: 'En curso',
  completado: 'Completado',
  error: 'Error',
}

export default function Asistente({ casoId = null }) {
  const [mensaje, setMensaje] = useState('')
  const [turnos, setTurnos] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [aviso, setAviso] = useState('')
  const conversacion = useRef({ casoId: null, id: null })
  const controlador = useRef(null)
  const bloqueo = useRef(false)
  const activo = useRef(true)
  const cajaMensaje = useRef(null)

  function ajustarCaja() {
    const caja = cajaMensaje.current
    if (!caja || caja.getBoundingClientRect().width === 0) return
    caja.style.height = 'auto'
    const limite = Math.max(36, Math.min(180, window.innerHeight * 0.25))
    const altura = Math.max(36, Math.min(caja.scrollHeight, limite))
    caja.style.height = `${altura}px`
    caja.style.overflowY = caja.scrollHeight > limite ? 'auto' : 'hidden'
  }

  useLayoutEffect(() => { ajustarCaja() }, [mensaje])

  useEffect(() => {
    let anchoAnterior = -1
    const observador = new ResizeObserver(([entrada]) => {
      if (entrada.contentRect.width !== anchoAnterior) {
        anchoAnterior = entrada.contentRect.width
        ajustarCaja()
      }
    })
    if (cajaMensaje.current) observador.observe(cajaMensaje.current)
    window.addEventListener('resize', ajustarCaja)
    return () => {
      observador.disconnect()
      window.removeEventListener('resize', ajustarCaja)
    }
  }, [])

  useEffect(() => {
    activo.current = true

    return () => {
      activo.current = false
      controlador.current?.abort()
    }
  }, [])

  function actualizar(id, cambio) {
    if (!activo.current) return

    setTurnos((anteriores) =>
      anteriores.map((turno) =>
        turno.id === id ? cambio(turno) : turno,
      ),
    )
  }

  async function enviar(evento) {
    evento.preventDefault()

    const texto = mensaje.trim()

    if (!texto || bloqueo.current) return

    if (texto.length > 2000) {
      setAviso('El mensaje no puede superar 2000 caracteres.')
      return
    }

    bloqueo.current = true
    setOcupado(true)
    setAviso('')
    setMensaje('')

    const id = crypto.randomUUID()
    const abortador = new AbortController()
    controlador.current = abortador

    setTurnos((anteriores) => [
      ...anteriores,
      {
        id,
        pregunta: texto,
        pasos: [],
        respuesta: '',
        simulado: true,
        fuentes: [],
        error: '',
        terminado: false,
        abierto: false,
        duracion: null,
      },
    ])

    let recibioRespuesta = false
    let falloPaso = false

    function procesarEvento(bloque) {
      let tipo = 'message'
      const datos = []

      for (const linea of bloque.split('\n')) {
        if (linea.startsWith('event:')) {
          tipo = linea.slice(6).trim()
        }

        if (linea.startsWith('data:')) {
          datos.push(linea.slice(5).trimStart())
        }
      }

      if (!datos.length) return

      const contenido = JSON.parse(datos.join('\n'))

      if (tipo === 'paso') {
        if (
          typeof contenido.id !== 'string' ||
          typeof contenido.texto !== 'string' ||
          !Object.hasOwn(ESTADOS, contenido.estado)
        ) {
          throw new Error('El servidor envió un paso inválido.')
        }

        if (contenido.estado === 'error') falloPaso = true

        actualizar(id, (turno) => {
          const existe = turno.pasos.some(
            (paso) => paso.id === contenido.id,
          )

          return {
            ...turno,
            pasos: existe
              ? turno.pasos.map((paso) =>
                  paso.id === contenido.id ? contenido : paso,
                )
              : [...turno.pasos, contenido],
          }
        })
      }

      if (tipo === 'respuesta') {
        if (typeof contenido.respuesta !== 'string' ||
            !['datos', 'politicas', 'informacion_general', 'mixta'].includes(contenido.tipo) ||
            (contenido.fuentes !== undefined && (!Array.isArray(contenido.fuentes) ||
              !contenido.fuentes.every((fuente) => typeof fuente === 'string')))) {
          throw new Error('El servidor envió una respuesta inválida.')
        }

        recibioRespuesta = true

        actualizar(id, (turno) => ({
          ...turno,
          respuesta: contenido.respuesta,
          simulado: contenido.simulado !== false,
          fuentes: contenido.fuentes ?? [],
          duracion: Number.isFinite(contenido.duracion_ms)
            ? contenido.duracion_ms
            : null,
        }))
      }
    }

    try {
      let conversacionId = null
      if (CHAT_REAL) {
        if (conversacion.current.casoId !== casoId) {
          conversacion.current = { casoId, id: null }
        }
        if (!conversacion.current.id) {
          const nueva = await fetch(CHAT_API + '/api/chat/conversaciones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...identidadApi() },
            body: JSON.stringify({ titulo: texto.slice(0, 200), caso_id: casoId }),
            signal: abortador.signal,
          })
          if (!nueva.ok) {
            throw new Error(`No se pudo abrir la conversación: HTTP ${nueva.status}.`)
          }
          const datos = await nueva.json()
          if (typeof datos.id !== 'string' || !datos.id) {
            throw new Error('El servidor no devolvió una conversación válida.')
          }
          conversacion.current = { casoId, id: datos.id }
        }
        conversacionId = conversacion.current.id
      }
      const respuesta = await fetch(CHAT_API + '/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...identidadApi(),
        },
        body: JSON.stringify({
          mensaje: texto,
          ...(conversacionId ? { conversacion_id: conversacionId } : {}),
          caso_id: casoId,
        }),
        signal: abortador.signal,
      })

      if (!respuesta.ok) {
        throw new Error(`La consulta falló: HTTP ${respuesta.status}.`)
      }

      if (
        !respuesta.headers
          .get('content-type')
          ?.includes('text/event-stream')
      ) {
        throw new Error('El servidor no devolvió eventos del chat.')
      }

      if (!respuesta.body) {
        throw new Error('La respuesta llegó sin contenido.')
      }

      const lector = respuesta.body.getReader()
      const decoder = new TextDecoder()
      let pendiente = ''

      try {
        while (true) {
          const { value, done } = await lector.read()

          pendiente += done
            ? decoder.decode()
            : decoder.decode(value, { stream: true })

          let separador

          while ((separador = /\r?\n\r?\n/.exec(pendiente))) {
            const bloque = pendiente.slice(0, separador.index)
            pendiente = pendiente.slice(
              separador.index + separador[0].length,
            )

            procesarEvento(bloque.replace(/\r\n/g, '\n'))
          }

          if (done) break
        }

        if (pendiente.trim()) {
          throw new Error('La transmisión terminó con un evento incompleto.')
        }
      } finally {
        await lector.cancel().catch(() => {})
        lector.releaseLock()
      }

      if (!recibioRespuesta || falloPaso) {
        throw new Error(
          falloPaso
            ? 'Un paso falló. Puedes editar tu pregunta y volver a enviarla.'
            : 'La conexión terminó sin una respuesta final.',
        )
      }
    } catch (error) {
      actualizar(id, (turno) => ({
        ...turno,
        error:
          error.name === 'AbortError'
            ? 'Consulta cancelada.'
            : error.message,
        pasos: turno.pasos.map((paso) =>
          paso.estado === 'en_curso'
            ? { ...paso, estado: 'error' }
            : paso,
        ),
      }))
    } finally {
      actualizar(id, (turno) => ({
        ...turno,
        terminado: true,
        abierto: false,
      }))

      bloqueo.current = false

      if (activo.current) {
        setOcupado(false)
        controlador.current = null
      }
    }
  }

  return (
    <section className="asistente" aria-label="Asistente de consultas">
      <div className="asistente-conversacion">
        {turnos.length === 0 && (
          <div className="chat-bienvenida"><span className="chat-robot"><Bot size={34} /></span><h2>¿En qué puedo ayudarte?</h2><p>Consulta políticas, revisa un caso y encuentra la evidencia.</p><div className="chat-sugerencias">{(casoId ? ['Consulta el detalle del caso', `¿Por qué se rechazó la factura ${casoId}?`] : ['Consulta las reglas de calidad de datos', '¿Qué significa calidad de datos?']).map(texto => <button key={texto} type="button" onClick={() => setMensaje(texto)}>{texto}</button>)}</div></div>
        )}

        {turnos.map((turno) => {
          const actual = turno.pasos.find(
            (paso) => paso.estado === 'en_curso',
          )

          const errores = turno.pasos.filter(
            (paso) => paso.estado === 'error',
          ).length

          const resumen = turno.terminado
            ? `${turno.pasos.length} pasos${errores ? ` · ${errores} con error` : ''}${turno.duracion !== null ? ` · ${(turno.duracion / 1000).toFixed(1)} s` : ''}`
            : actual?.texto || 'Esperando respuesta…'

          return (
            <article key={turno.id} className="asistente-turno">
              <div className="asistente-pregunta">
                <strong>Tú</strong>
                <p>{turno.pregunta}</p>
              </div>

              <button
                type="button"
                className="asistente-pasos-boton"
                aria-expanded={turno.abierto}
                aria-controls={`pasos-${turno.id}`}
                onClick={() =>
                  actualizar(turno.id, (anterior) => ({
                    ...anterior,
                    abierto: !anterior.abierto,
                  }))
                }
              >
                {turno.abierto ? '▾' : '▸'} {resumen}
              </button>

              <div role="status" className="asistente-sr">
                {resumen}
              </div>

              <ol
                id={`pasos-${turno.id}`}
                hidden={!turno.abierto}
                className="asistente-pasos"
              >
                {turno.pasos.map((paso) => (
                  <li key={paso.id}>
                    <strong>{paso.texto}</strong>
                    {' — '}
                    {ESTADOS[paso.estado]}
                    {paso.detalle && <p>{paso.detalle}</p>}
                  </li>
                ))}
              </ol>

              {turno.respuesta && (
                <div className="asistente-respuesta">
                  <strong className="chat-autor"><Bot size={18} />{turno.simulado ? 'Asistente · simulación' : 'Asistente'}</strong>
                  <p>{turno.respuesta}</p>
                  {turno.fuentes.length > 0 && (
                    <section aria-label="Fuentes de la respuesta">
                      <strong>Fuentes</strong>
                      <ul>
                        {turno.fuentes.map((fuente, indice) => (
                          <li key={`${indice}-${fuente}`}>{fuente}</li>
                        ))}
                      </ul>
                    </section>
                  )}
                </div>
              )}

              {turno.error && (
                <div className="asistente-error" role="alert">
                  <p>{turno.error}</p>
                  <button
                    type="button"
                    className="btn"
                    disabled={ocupado}
                    onClick={() => setMensaje(turno.pregunta)}
                  >
                    Recuperar pregunta
                  </button>
                </div>
              )}
            </article>
          )
        })}
      </div>

      <form onSubmit={enviar} className="asistente-formulario">
        <label htmlFor="mensaje-asistente">Tu pregunta</label>
        <textarea
          id="mensaje-asistente"
          ref={cajaMensaje}
          enterKeyHint="send"
          aria-describedby="ayuda-mensaje-asistente"
          onKeyDown={(evento) => {
            if (evento.key === 'Enter' && !evento.shiftKey && !evento.nativeEvent.isComposing && evento.keyCode !== 229) {
              evento.preventDefault()
              if (!evento.repeat) evento.currentTarget.form.requestSubmit()
            }
          }}
          value={mensaje}
          onChange={(evento) => setMensaje(evento.target.value)}
          maxLength={2000}
          rows={1}
          disabled={ocupado}
          placeholder="Escribe tu pregunta…"
        />
        {aviso && <p role="alert">{aviso}</p>}

        <span id="ayuda-mensaje-asistente" className="asistente-sr">Enter para enviar. Shift más Enter para una nueva línea.</span>
          <div className="asistente-acciones">
          <span>{mensaje.length}/2000</span>

          {ocupado && (
            <button
              type="button"
              className="btn"
              onClick={() => controlador.current?.abort()}
            >
              <Square size={14} /> Cancelar
            </button>
          )}

          <button
            type="submit"
            className="btn btn-primario"
            disabled={ocupado || !mensaje.trim()}
          >
            {ocupado ? <><Loader size={17} className="girando" aria-hidden="true" />Consultando…</> : <><ArrowUp size={17} /> Enviar</>}
          </button>
        </div>
      </form>
    </section>
  )
}