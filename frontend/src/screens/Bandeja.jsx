import { useEffect, useState } from 'react'
import {
  Plus, Search, ChevronDown, Calendar, Loader, Eye, TriangleAlert, Check,
  ArrowDown, Inbox, CircleAlert, RotateCw,
} from 'lucide-react'
import { Estado, Resultado, Banner } from '../components.jsx'
import { CASOS } from '../data.js'
import { CASOS_REALES, obtenerCasos } from '../api.js'

export default function Bandeja({ variante = 'normal', abrirCaso, ir, setVariante }) {
  const [buscar, setBuscar] = useState('')
  const [casos, setCasos] = useState([])
  const [metricas, setMetricas] = useState(null)
  const [cargando, setCargando] = useState(variante === 'cargando')
  const [errorCarga, setErrorCarga] = useState(variante === 'error')
  const [filtroEstado, setFiltroEstado] = useState('todos')
  const [filtroTipo, setFiltroTipo] = useState('todos')
  const [filtroResultado, setFiltroResultado] = useState('todos')

  useEffect(() => {
    if (variante === 'vacio') {
      setCasos([])
      setCargando(false)
      setErrorCarga(false)
      return
    }
    if (variante === 'cargando') {
      setCargando(true)
      setErrorCarga(false)
      return
    }
    if (variante === 'error') {
      setErrorCarga(true)
      setCargando(false)
      return
    }

    let cancelado = false
    setCargando(true)
    setErrorCarga(false)

    obtenerCasos()
      .then((data) => {
        if (!cancelado) {
          setCasos(data.casos || [])
          setMetricas(data.metricas || null)
          setCargando(false)
        }
      })
      .catch((err) => {
        if (!cancelado) {
          if (!CASOS_REALES) console.warn('API no disponible, usando datos de respaldo:', err)
          setCasos(CASOS_REALES ? [] : CASOS)
          setErrorCarga(Boolean(CASOS_REALES))
          setCargando(false)
        }
      })

    return () => { cancelado = true }
  }, [variante])

  const filtrados = casos.filter((c) => {
    const coincideTexto = `${c.id} ${c.archivo}`.toLowerCase().includes(buscar.toLowerCase())
    const coincideEstado = filtroEstado === 'todos' || c.estado === filtroEstado
    const coincideTipo = filtroTipo === 'todos' || c.tipo === filtroTipo
    const coincideResultado = filtroResultado === 'todos' || c.resultado === filtroResultado
    return coincideTexto && coincideEstado && coincideTipo && coincideResultado
  })

  let contenido
  if (cargando) {
    contenido = (
      <div className="esqueleto">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} style={{ width: `${70 + ((i * 7) % 25)}%` }} />
        ))}
      </div>
    )
  } else if (errorCarga) {
    contenido = (
      <div style={{ padding: 24, display: 'grid', gap: 16, justifyItems: 'start' }}>
        <Banner tipo="error" icono={CircleAlert}>
          <b>No pudimos cargar los casos</b><br />Revisa tu conexión e inténtalo de nuevo.
        </Banner>
        <button className="btn" onClick={() => { setErrorCarga(false); setVariante('normal') }}>
          <RotateCw size={18} />Reintentar
        </button>
      </div>
    )
  } else if (casos.length === 0) {
    contenido = (
      <div className="vacio">
        <span className="ico"><Inbox size={24} /></span>
        <p>Aún no hay casos. Sube tu primer archivo</p>
        <button className="btn btn-primario" onClick={() => ir('subir')}>Subir caso</button>
      </div>
    )
  } else {
    contenido = (
      <>
        <table className="tabla">
          <thead>
            <tr>
              <th>ID del caso <ArrowDown size={14} style={{ verticalAlign: -2 }} /></th>
              <th>Archivo</th><th>Tipo de revisión</th><th>Estado</th>
              <th>Resultado sugerido</th><th>Fecha</th><th>Responsable</th>
            </tr>
          </thead>
          <tbody>
            {filtrados.map((c) => (
              <tr key={c.id} className="click" onClick={() => abrirCaso(c)}>
                <td><span className="id-caso">{c.id}</span></td>
                <td>{c.archivo}</td>
                <td>{c.tipo}</td>
                <td><Estado valor={c.estado} /></td>
                <td><Resultado valor={c.resultado} /></td>
                <td className="num">{c.fecha}</td>
                <td>{c.responsable}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pie-tabla">
          <span>Mostrando {filtrados.length} de {casos.length} casos</span>
          <span>Resultado sugerido por el agente · la decisión es de la persona revisora</span>
        </div>
      </>
    )
  }

  const statProcesando = metricas?.procesando ?? casos.filter((c) => c.estado === 'procesando').length
  const statEnRevision = metricas?.en_revision ?? casos.filter((c) => c.estado === 'revision').length
  const statHumana = casos.filter((c) => c.resultado === 'humana').length
  const statRevisados = metricas?.revisados ?? casos.filter((c) => c.estado === 'revisado').length

  const statsDinamicos = [
    [Loader, 'Procesando', 'var(--info)', statProcesando],
    [Eye, 'En revisión', 'var(--texto)', statEnRevision],
    [TriangleAlert, 'Requieren revisión humana', 'var(--adv)', statHumana],
    [Check, 'Revisados hoy', 'var(--exito)', statRevisados],
  ]

  return (
    <main className="main">
      <div className="cabecera">
        <div>
          <h1>Casos</h1>
          <p>Revisa los resultados sugeridos por el agente y confirma o escala cada caso.</p>
        </div>
        <button className="btn btn-primario" onClick={() => ir('subir')}><Plus size={20} />Subir caso</button>
      </div>

      <div className="stats">
        {statsDinamicos.map(([Icono, texto, color, valor]) => (
          <div className="tarjeta stat" key={texto}>
            <div className="t" style={{ color }}><Icono size={20} />{texto}</div>
            <div className="n num">{cargando ? '–' : valor}</div>
          </div>
        ))}
      </div>

      <div className="tarjeta">
        <div className="filtros">
          <label className="buscar">
            <Search size={18} color="var(--texto-2)" />
            <input placeholder="Buscar por ID o archivo" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
          </label>
          <button
            className="select"
            onClick={() => setFiltroEstado((e) => (e === 'todos' ? 'revision' : e === 'revision' ? 'revisado' : e === 'revisado' ? 'procesando' : 'todos'))}
          >
            Estado: {filtroEstado} <ChevronDown size={16} />
          </button>
          <button
            className="select"
            onClick={() => setFiltroTipo((t) => (t === 'todos' ? 'Factura' : t === 'Factura' ? 'Validación con políticas' : 'todos'))}
          >
            Tipo: {filtroTipo} <ChevronDown size={16} />
          </button>
          <button
            className="select"
            onClick={() => setFiltroResultado((r) => (r === 'todos' ? 'humana' : r === 'humana' ? 'aceptado' : r === 'aceptado' ? 'rechazado' : 'todos'))}
          >
            Resultado: {filtroResultado} <ChevronDown size={16} />
          </button>
          <button className="select"><Calendar size={16} />Últimos 7 días</button>
        </div>
        {contenido}
      </div>
    </main>
  )
}
