import { useState } from 'react'
import {
  Plus, Search, ChevronDown, Calendar, Loader, Eye, TriangleAlert, Check,
  ArrowDown, Inbox, CircleAlert, RotateCw,
} from 'lucide-react'
import { Estado, Resultado, Banner } from '../components.jsx'
import { CASOS } from '../data.js'

const STATS = [
  [Loader, 'Procesando', 'var(--info)'],
  [Eye, 'En revisión', 'var(--texto)'],
  [TriangleAlert, 'Requieren revisión humana', 'var(--adv)'],
  [Check, 'Revisados hoy', 'var(--exito)'],
]

export default function Bandeja({ variante = 'normal', abrirCaso, ir, setVariante }) {
  const [buscar, setBuscar] = useState('')
  const casos = variante === 'vacio' ? [] : CASOS
  const filtrados = casos.filter((c) =>
    `${c.id} ${c.archivo}`.toLowerCase().includes(buscar.toLowerCase()))

  let contenido
  if (variante === 'cargando') {
    contenido = (
      <div className="esqueleto">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} style={{ width: `${70 + ((i * 7) % 25)}%` }} />
        ))}
      </div>
    )
  } else if (variante === 'error') {
    contenido = (
      <div style={{ padding: 24, display: 'grid', gap: 16, justifyItems: 'start' }}>
        <Banner tipo="error" icono={CircleAlert}>
          <b>No pudimos cargar los casos</b><br />Revisa tu conexión e inténtalo de nuevo.
        </Banner>
        <button className="btn" onClick={() => setVariante('normal')}><RotateCw size={18} />Reintentar</button>
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

  const n = variante === 'normal' ? 1 : 0
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
        {STATS.map(([Icono, texto, color]) => (
          <div className="tarjeta stat" key={texto}>
            <div className="t" style={{ color }}><Icono size={20} />{texto}</div>
            <div className="n num">{variante === 'cargando' ? '–' : n}</div>
          </div>
        ))}
      </div>

      <div className="tarjeta">
        <div className="filtros">
          <label className="buscar">
            <Search size={18} color="var(--texto-2)" />
            <input placeholder="Buscar por ID o archivo" value={buscar} onChange={(e) => setBuscar(e.target.value)} />
          </label>
          <button className="select">Estado: todos <ChevronDown size={16} /></button>
          <button className="select">Tipo de revisión: todos <ChevronDown size={16} /></button>
          <button className="select">Resultado sugerido: todos <ChevronDown size={16} /></button>
          <button className="select"><Calendar size={16} />Últimos 7 días</button>
        </div>
        {contenido}
      </div>
    </main>
  )
}
