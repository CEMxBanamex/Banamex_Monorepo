import { useEffect, useState } from 'react'
import { obtenerDetalleCaso, registrarDecisionCaso } from '../api.js'

export default function DetalleReal({ casoId, ir, toast }) {
  const [caso, setCaso] = useState(null)
  const [error, setError] = useState('')
  const [motivo, setMotivo] = useState('')
  const [resultado, setResultado] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    let activo = true
    obtenerDetalleCaso(casoId)
      .then((detalle) => { if (activo) setCaso(detalle) })
      .catch((err) => { if (activo) setError(err.message) })
    return () => { activo = false }
  }, [casoId])

  async function decidir(evento) {
    evento.preventDefault()
    setGuardando(true)
    setError('')
    try {
      const decision = await registrarDecisionCaso(casoId, {
        accion: 'confirmar', resultado, comentario: motivo.trim(),
      })
      setCaso((anterior) => ({ ...anterior, estado: decision.estado, resultado_final: decision.resultado_final }))
      toast({ texto: 'Decisión registrada en la bitácora' })
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <main className="main">
      <button type="button" className="btn" onClick={() => ir('casos')}>Volver a casos</button>
      <h1>{caso?.archivo || casoId}</h1>
      {error && <p role="alert">{error}</p>}
      {!caso && !error && <p role="status">Cargando caso…</p>}
      {caso && (
        <>
          <p>{caso.id} · {caso.estado}{caso.resultado_final ? ` · ${caso.resultado_final}` : ''}</p>
          {caso.estado === 'error' && <p>El análisis falló. Revisa el archivo y vuelve a subirlo si es necesario.</p>}
          <div className="det-grid">
            <section className="tarjeta tarjeta-pad">
              <h2>Documento original</h2>
              {caso.documento_url
                ? <img src={caso.documento_url} alt={caso.archivo} style={{ maxWidth: '100%' }} />
                : <p>El caso no tiene una imagen disponible.</p>}
            </section>
            <section className="tarjeta tarjeta-pad">
              <h2>Hallazgos</h2>
              {caso.explicacion && <p style={{ whiteSpace: 'pre-wrap' }}>{caso.explicacion}</p>}
              {caso.hallazgos.map((hallazgo) => (
                <article key={hallazgo.id}>
                  <h3>{hallazgo.titulo}</h3>
                  <p>{hallazgo.regla} v{hallazgo.version} · {hallazgo.texto}</p>
                  {hallazgo.evidencia && <p>{hallazgo.evidencia}</p>}
                </article>
              ))}
              {caso.campos.length > 0 && (
                <>
                  <h2>Campos extraídos</h2>
                  <dl>{caso.campos.map((campo) => (
                    <div key={campo.id}><dt>{campo.etiqueta}</dt><dd>{campo.valor ?? 'Sin dato'}</dd></div>
                  ))}</dl>
                </>
              )}
            </section>
          </div>
          {caso.estado === 'revision' && caso.tipo === 'Factura' && (
            <form className="tarjeta tarjeta-pad" onSubmit={decidir}>
              <h2>Decisión del analista</h2>
              <label>Resultado
                <select value={resultado} onChange={(e) => setResultado(e.target.value)} required>
                  <option value="">Elige un resultado</option>
                  <option value="aceptado">Aceptar</option>
                  <option value="rechazado">Rechazar</option>
                </select>
              </label>
              <label>Motivo <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} required /></label>
              <button className="btn btn-primario" disabled={guardando || !resultado || !motivo.trim()}>
                {guardando ? 'Guardando…' : 'Registrar decisión'}
              </button>
            </form>
          )}
          <button type="button" className="btn" onClick={() => ir('bitacora')}>Ver bitácora</button>
        </>
      )}
    </main>
  )
}
