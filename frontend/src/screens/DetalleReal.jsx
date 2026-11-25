import { useEffect, useState } from 'react'
import { ArrowLeft, Check, ClipboardList, FileText, ListChecks, X } from 'lucide-react'
import { obtenerDetalleCaso, registrarDecisionCaso } from '../api.js'
import './DetalleReal.css'

const ESTADOS = { revision: 'En revisión', revisado: 'Revisado', procesando: 'En proceso', error: 'Error de análisis' }
const RESULTADOS = { aceptado: 'Aceptado', rechazado: 'Rechazado' }

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
    <main className="main caso-real">
      <header className="caso-real__cabecera">
        <button type="button" className="btn caso-real__accion" onClick={() => ir('casos')}>
          <ArrowLeft size={17} aria-hidden="true" /> Volver a casos
        </button>
        {caso && <button type="button" className="btn caso-real__accion" onClick={() => ir('bitacora')}>
          <ClipboardList size={17} aria-hidden="true" /> Ver bitácora
        </button>}
        <div className="caso-real__titulo">
          <h1>{caso?.archivo || casoId}</h1>
          {caso && <div className="caso-real__estado">
            {caso.archivo && caso.archivo !== caso.id && <span>{caso.id}</span>}
            <span className="caso-real__pildora" data-estado={caso.estado}>{ESTADOS[caso.estado] ?? caso.estado}</span>
            {caso.resultado_final && <span>{RESULTADOS[caso.resultado_final] ?? caso.resultado_final}</span>}
          </div>}
        </div>
      </header>

      {error && !caso && <p className="caso-real__error" role="alert">{error}</p>}
      {!caso && !error && <p role="status">Cargando caso…</p>}
      {caso && (
        <>
          {caso.estado === 'error' && <p className="caso-real__error">El análisis falló. Revisa el archivo y vuelve a subirlo si es necesario.</p>}
          <div className={caso.documento_url ? 'caso-real__grid' : 'caso-real__grid caso-real__grid--sin-documento'}>
            <div className="caso-real__columna">
              <section className="tarjeta caso-real__panel">
                <h2><FileText size={19} aria-hidden="true" /> Documento original</h2>
                {caso.documento_url
                  ? <div className="caso-real__visor">
                      {caso.archivo?.toLowerCase().endsWith('.xml')
                        ? <p><a href={caso.documento_url} target="_blank" rel="noreferrer" download={caso.archivo}>Descargar XML original</a></p>
                        : caso.archivo?.toLowerCase().endsWith('.pdf')
                        ? <object data={caso.documento_url} type="application/pdf" aria-label={caso.archivo}>
                            <a href={caso.documento_url} target="_blank" rel="noreferrer">Abrir PDF original</a>
                          </object>
                        : <img src={caso.documento_url} alt={caso.archivo} />}
                    </div>
                  : <p className="caso-real__vacio">Este caso no tiene una imagen disponible.</p>}
              </section>
            </div>
            <div className="caso-real__columna">
              <section className="tarjeta caso-real__panel">
                <h2><ListChecks size={19} aria-hidden="true" /> Hallazgos</h2>
                {caso.revision_evidencia && <p className="caso-real__aviso" role="note">Compara los datos leídos con el documento original antes de registrar tu decisión.</p>}
                {caso.explicacion && <p className="caso-real__resumen">{caso.explicacion}</p>}
                {!caso.explicacion && caso.hallazgos.length === 0 && <p className="caso-real__vacio">Sin hallazgos registrados.</p>}
                {caso.hallazgos.map((hallazgo) => (
                  <article key={hallazgo.id} className="caso-real__hallazgo">
                    <span className="caso-real__regla">{hallazgo.regla} v{hallazgo.version}</span>
                    <h3>{hallazgo.titulo}</h3>
                    <p>{hallazgo.texto}</p>
                    {hallazgo.evidencia && <p className="muted">{hallazgo.evidencia}</p>}
                  </article>
                ))}
              </section>
              {caso.campos.length > 0 && (
                <section className="tarjeta caso-real__panel">
                  <h2>Campos extraídos</h2>
                  {caso.origen_extraccion === 'xml_cfdi' && <p>Datos leídos del XML sin modelo. No se ha validado su autenticidad ni estatus ante el SAT.</p>}
                  {caso.uuid_fiscal && <p><strong>UUID declarado:</strong> {caso.uuid_fiscal}</p>}
                  <dl className="caso-real__campos">{caso.campos.map((campo) => (
                    <div key={campo.id}>
                      <dt>{campo.etiqueta}</dt>
                      <dd>{campo.valor ?? 'Sin valor leído'}</dd>
                      {campo.estado_evidencia === 'pendiente_revision' && <dd className="caso-real__evidencia">Evidencia incompleta. Comprueba el original.</dd>}
                    </div>
                  ))}</dl>
                </section>
              )}
              {caso.conceptos?.length > 0 && (
                <section className="tarjeta caso-real__panel">
                  <h2>Conceptos leídos</h2>
                  <div className="caso-real__tabla">
                    <table>
                      <thead><tr><th>Descripción</th><th>Cantidad</th><th>Precio unitario</th><th>Importe</th></tr></thead>
                      <tbody>{caso.conceptos.map((concepto, i) => (
                        <tr key={i}>
                          <td>{concepto.descripcion}</td><td>{concepto.cantidad ?? 'Sin lectura'}</td>
                          <td>{concepto.precio_unitario ?? 'Sin lectura'}</td><td>{concepto.importe ?? 'Sin lectura'}</td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                </section>
              )}
            </div>
          </div>
          {caso.estado === 'revision' && caso.tipo === 'Factura' && (
            <form className="tarjeta caso-real__panel caso-real__decision" onSubmit={decidir}>
              <h2>Decisión del analista</h2>
              <fieldset>
                <legend>Resultado</legend>
                <div className="caso-real__opciones">
                  <label className="caso-real__opcion">
                    <input type="radio" name="resultado" value="aceptado" required disabled={guardando}
                      checked={resultado === 'aceptado'} onChange={(e) => setResultado(e.target.value)} />
                    <Check size={18} aria-hidden="true" /> Aceptar
                  </label>
                  <label className="caso-real__opcion">
                    <input type="radio" name="resultado" value="rechazado" disabled={guardando}
                      checked={resultado === 'rechazado'} onChange={(e) => setResultado(e.target.value)} />
                    <X size={18} aria-hidden="true" /> Rechazar
                  </label>
                </div>
              </fieldset>
              <label className="caso-real__motivo">
                Motivo
                <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3}
                  placeholder="Escribe el motivo de tu decisión" required disabled={guardando} />
              </label>
              {error && <p className="caso-real__error" role="alert">{error}</p>}
              <div className="caso-real__pie">
                <button className="btn btn-primario" disabled={guardando || !resultado || !motivo.trim()}>
                  {guardando ? 'Guardando…' : 'Registrar decisión'}
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </main>
  )
}
