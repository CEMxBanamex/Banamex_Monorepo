import { useState } from 'react'
import { CircleX, Shield, Table, Check, Flag, Pencil } from 'lucide-react'
import { Dialogo } from '../components.jsx'
import { Cabecera, BarraAcciones, ResultadoSugerido } from './Detalle.jsx'
import { POLITICAS, REGISTROS, FILAS_FALTANTES } from '../data.js'

export default function Validacion({ caso, ir, toast }) {
  const [dialogo, setDialogo] = useState(false)
  const [estado, setEstado] = useState('revision')
  const [eventos, setEventos] = useState(3)

  return (
    <main className="main con-barra">
      <Cabecera caso={caso} estado={estado} resultado="rechazado" volver={() => ir('casos')} />
      <div className="det-grid validacion">
        <section className="tarjeta" style={{ overflow: 'hidden' }}>
          <div className="visor-cab" style={{ padding: '14px 20px' }}>
            <b style={{ fontWeight: 600 }}>Registros · hoja «clientes»</b>
            <div style={{ display: 'flex', gap: 18 }}>
              <span className="muted">120 registros</span>
              <span className="leyenda"><i />Celda con problema</span>
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="tabla registros">
              <thead>
                <tr><th /><th>id_cliente</th><th>nombre</th><th>rfc</th><th>correo_contacto</th><th>alta</th></tr>
              </thead>
              <tbody className="num">
                {REGISTROS.map((r, i) =>
                  r.salto ? (
                    <tr key={i} className="salto"><td>…</td><td colSpan={5}>filas {r.salto}</td></tr>
                  ) : (
                    <tr key={i} className={r.correo ? '' : 'prob'}>
                      <td>{r.fila}</td><td>{r.id}</td><td>{r.nombre}</td><td>{r.rfc}</td>
                      <td className={r.correo ? '' : 'celda-prob'}>{r.correo || 'vacío'}</td>
                      <td>{r.alta}</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </section>

        <div className="col">
          <section className="tarjeta tarjeta-pad">
            <h2 style={{ marginBottom: 16 }}>Hallazgos <span className="muted" style={{ fontWeight: 400 }}>(1)</span></h2>
            <div className="hallazgo sel">
              <CircleX size={22} color="var(--error)" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <h4>Campo obligatorio faltante: <code className="chip mono" style={{ padding: '1px 6px' }}>correo_contacto</code></h4>
                <p>8 de 120 registros no tienen correo de contacto. La política exige este campo para todo cliente dado de alta.</p>
                <div className="cifras" style={{ gridTemplateColumns: '1fr' }}>
                  <div><small>Filas afectadas</small><b className="num">{FILAS_FALTANTES.join(', ')}</b></div>
                </div>
                <div className="chips">
                  <span className="chip"><Shield size={14} />Regla P-007</span>
                  <span className="chip">Versión 1.3</span>
                  <span className="chip"><Table size={14} />Evidencia: columna correo_contacto</span>
                </div>
              </div>
            </div>
          </section>

          <section className="tarjeta tarjeta-pad">
            <h2 style={{ marginBottom: 6 }}>Políticas consultadas</h2>
            {POLITICAS.map((p) => (
              <div className="politica" key={p.id}>
                <div><b>{p.id} · {p.nombre}</b><small>Versión {p.version} · vigencia {p.vigencia}</small></div>
                <span className="badge b-exito" style={{ alignSelf: 'flex-start' }}><Check size={16} />Vigente</span>
              </div>
            ))}
          </section>

          <ResultadoSugerido resultado="rechazado">
            El archivo no cumple la política P-007 porque 8 registros no tienen correo de contacto. Las otras dos políticas se cumplen.
          </ResultadoSugerido>
        </div>
      </div>

      <BarraAcciones
        eventos={eventos}
        verBitacora={() => ir('bitacora')}
        onCorregir={() => toast({ texto: 'La corrección de registros se hace en el archivo de origen', icono: Pencil, color: '#9cc7e8' })}
        onEscalar={() => { setEventos((e) => e + 1); toast({ texto: 'Caso escalado a supervisión', icono: Flag, color: '#f2c14e' }) }}
        onConfirmar={() => setDialogo(true)}
      />
      {dialogo && (
        <Dialogo
          titulo="Confirmar resultado"
          onCancelar={() => setDialogo(false)}
          onConfirmar={() => {
            setDialogo(false); setEstado('revisado'); setEventos((e) => e + 1)
            toast({ texto: 'Resultado confirmado y registrado en la bitácora' })
          }}
        >
          <p>Vas a confirmar el resultado sugerido <b>Rechazado</b> para el caso {caso.id}. Quedará registrado en la bitácora.</p>
          <p style={{ fontSize: 15 }}>Esta confirmación no autoriza pagos ni operaciones.</p>
        </Dialogo>
      )}
    </main>
  )
}
