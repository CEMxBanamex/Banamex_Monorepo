import { Fragment, useState } from 'react'
import { Download, Lock, ChevronDown, ChevronRight, Calendar, Bot } from 'lucide-react'
import { EVENTOS } from '../data.js'

const TONOS = {
  exito: ['var(--exito-bg)', 'var(--exito)'],
  adv: ['var(--adv-bg)', 'var(--adv)'],
  info: ['var(--info-bg)', 'var(--info)'],
  error: ['var(--error-bg)', 'var(--error)'],
}

export default function Bitacora({ toast }) {
  const [abierto, setAbierto] = useState('EV-3108')

  return (
    <main className="main">
      <div className="cabecera">
        <div>
          <h1>Bitácora</h1>
          <p><Lock size={16} />Registro de solo lectura de todas las acciones de personas y del agente.</p>
        </div>
        <button className="btn" onClick={() => toast({ texto: 'Exportación simulada: en el prototipo no se descarga nada', icono: Download, color: '#9cc7e8' })}>
          <Download size={20} />Exportar
        </button>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
        <button className="select">Caso: todos <ChevronDown size={16} /></button>
        <button className="select">Usuario: todos <ChevronDown size={16} /></button>
        <button className="select">Tipo de acción: todas <ChevronDown size={16} /></button>
        <button className="select"><Calendar size={16} />25 oct – 26 oct 2026</button>
      </div>

      <div className="tarjeta">
        <table className="tabla bit">
          <thead>
            <tr><th style={{ width: 40 }} /><th>Fecha y hora</th><th>Caso</th><th>Quién</th><th>Acción</th><th>Detalle</th><th>Regla y versión</th></tr>
          </thead>
          <tbody>
            {EVENTOS.map((ev) => {
              const abiertoEste = abierto === ev.id
              const [bg, fg] = TONOS[ev.tono]
              return (
                <Fragment key={ev.id}>
                  <tr className="click" onClick={() => setAbierto(abiertoEste ? null : ev.id)} style={abiertoEste ? { borderBottom: 0 } : null}>
                    <td>
                      <button className="expandir" aria-expanded={abiertoEste} aria-label="Ver detalle">
                        {abiertoEste ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      </button>
                    </td>
                    <td className="num" style={{ maxWidth: 140 }}>{ev.fecha}</td>
                    <td><span className="id-caso" style={{ color: 'var(--texto)' }}>{ev.caso}</span></td>
                    <td>
                      <span className="quien">
                        {ev.ini ? <span className="avatar avatar-sm">{ev.ini}</span> : <span className="ico-agente"><Bot size={15} /></span>}
                        {ev.quien}
                      </span>
                    </td>
                    <td><span className="accion" style={{ background: bg, color: fg }}>{ev.accion}</span></td>
                    <td>{ev.detalle}</td>
                    <td className="muted num">{ev.regla || '—'}</td>
                  </tr>
                  {abiertoEste && (
                    <tr>
                      <td />
                      <td colSpan={6} style={{ paddingTop: 0 }}>
                        <div className="det-ev">
                          <p>{ev.extra?.texto || ev.detalle + '.'}</p>
                          {ev.extra && (
                            <p className="num">
                              <span className="muted">Valor anterior</span>{' '}
                              <s className="muted">{ev.extra.antes}</s>{'  '}
                              <span className="muted" style={{ marginLeft: 12 }}>Valor nuevo</span> <b>{ev.extra.despues}</b>
                            </p>
                          )}
                          <div className="chips">
                            <span className="chip">ID de evento {ev.id}</span>
                            <span className="chip">Origen: {ev.ini ? 'Interfaz web' : 'Agente'}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{ marginTop: 20 }}>Los eventos no se pueden editar ni eliminar.</p>
    </main>
  )
}
