import { useEffect, useState } from 'react'
import {
  ChevronLeft, ZoomIn, ZoomOut, TriangleAlert, CircleAlert, Shield, File,
  Info, List, Pencil, Flag, Check, ArrowRight, CircleCheck, RotateCw, Save,
} from 'lucide-react'
import { Estado, Resultado, Banner, Dialogo } from '../components.jsx'
import { CAMPOS_FACTURA, HALLAZGOS_FACTURA } from '../data.js'

const RESULTADO_TXT = { aceptado: 'Aceptado', rechazado: 'Rechazado', humana: 'Requiere revisión humana' }

export function Cabecera({ caso, estado, resultado, volver }) {
  return (
    <>
      <button className="volver" onClick={volver}><ChevronLeft size={18} />Casos</button>
      <div className="det-cab">
        <div className="izq">
          <h1>{caso.id}</h1>
          <span className="muted" style={{ fontSize: 18 }}>{caso.archivo} · {caso.tipo}</span>
        </div>
        <div className="der">
          Estado <Estado valor={estado} />
          <span style={{ width: 12 }} />
          Resultado sugerido <Resultado valor={resultado} />
        </div>
      </div>
    </>
  )
}

export function BarraAcciones({ eventos, verBitacora, onCorregir, corrigiendo, onEscalar, onConfirmar, deshabilitada }) {
  return (
    <div className="barra-acciones">
      <input placeholder="Agrega un comentario (opcional)" disabled={deshabilitada} />
      <button className="link" onClick={verBitacora}><List size={18} />Bitácora: {eventos} eventos</button>
      <button className="btn" onClick={onCorregir} disabled={deshabilitada}>
        {corrigiendo ? <><Save size={18} />Guardar corrección</> : <><Pencil size={18} />Corregir dato</>}
      </button>
      <button className="btn" onClick={onEscalar} disabled={deshabilitada}><Flag size={18} />Escalar caso</button>
      <button className="btn btn-primario" onClick={onConfirmar} disabled={deshabilitada}><Check size={18} />Confirmar resultado</button>
    </div>
  )
}

export function ResultadoSugerido({ resultado, children }) {
  return (
    <section className="tarjeta tarjeta-pad">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2>Resultado sugerido</h2><Resultado valor={resultado} />
      </div>
      {children && <p style={{ lineHeight: 1.65, margin: '0 0 18px', fontSize: 16 }}>{children}</p>}
      <Banner tipo="info" icono={Info}>Este resultado indica el cumplimiento de las reglas evaluadas. No autoriza pagos ni operaciones.</Banner>
    </section>
  )
}

function Documento({ resaltar, pagina, setPagina }) {
  const [zoom, setZoom] = useState(100)
  return (
    <section className="tarjeta">
      <div className="visor-cab">
        <b style={{ fontWeight: 600 }}>Documento original</b>
        <div className="ctrl">
          <button className="btn btn-icono" aria-label="Alejar" onClick={() => setZoom((z) => Math.max(50, z - 25))}><ZoomOut size={18} /></button>
          <span className="num" style={{ width: 52, textAlign: 'center' }}>{zoom} %</span>
          <button className="btn btn-icono" aria-label="Acercar" onClick={() => setZoom((z) => Math.min(200, z + 25))}><ZoomIn size={18} /></button>
          <span className="muted" style={{ borderLeft: '1px solid var(--borde)', paddingLeft: 14 }}>Página {pagina} de 2</span>
        </div>
      </div>
      <div className="visor-cuerpo">
        <div className="miniaturas">
          {[1, 2].map((p) => (
            <button key={p} style={{ background: 'none', border: 0, padding: 0 }} onClick={() => setPagina(p)}>
              <div className={`mini ${pagina === p ? 'activa' : ''}`}>
                <i style={{ width: '50%', height: 5 }} /><i /><i /><i style={{ width: '70%' }} />
                {p === 1 && <i style={{ width: 26, height: 6, background: 'var(--adv-borde)', marginTop: 40, justifySelf: 'end' }} />}
              </div>
              <div className="mini-et">{p}</div>
            </button>
          ))}
        </div>
        <div className="lienzo">
          <div className="hoja" style={{ transform: `scale(${zoom / 100})` }}>
            {pagina === 2 ? (
              <p className="muted">Página 2 · Términos y condiciones del proveedor (sin datos relevantes para la revisión).</p>
            ) : (
              <>
                <div className="cab">
                  <div>
                    <h3>Proveedor Demo SA</h3>
                    RFC XAXX010101000<br />Calle Ejemplo 123, Ciudad de México
                  </div>
                  <div className="der">
                    <b style={{ letterSpacing: 1 }}>FACTURA</b><br />Folio A-1042<br />
                    <span className={resaltar === 'fecha' ? 'resaltado' : ''} style={{ padding: '0 4px', whiteSpace: 'nowrap' }}>Fecha 12/03/2026</span>
                  </div>
                </div>
                <b>Receptor</b><br />Cliente de prueba SA de CV
                <table>
                  <thead><tr><th>Concepto</th><th className="r">Cant.</th><th className="r">Importe</th></tr></thead>
                  <tbody className="num">
                    <tr><td>Servicio de consultoría</td><td className="r">1</td><td className="r">8,000.00</td></tr>
                    <tr><td>Licencia anual de software</td><td className="r">1</td><td className="r">2,000.00</td></tr>
                  </tbody>
                </table>
                <div className="totales num">
                  <div><span>Subtotal</span><span>10,000.00</span></div>
                  <div><span>IVA 16 %</span><span>1,600.00</span></div>
                  <div className={`tot ${resaltar === 'total' ? 'resaltado' : ''}`}><span>Total</span><span>12,000.00</span></div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

function Confianza({ valor }) {
  const color = valor < 80 ? 'var(--adv-borde)' : 'var(--exito)'
  return (
    <div className="conf">
      <div className="pista"><div style={{ width: `${valor}%`, background: color }} /></div>
      <span className="num" style={valor < 80 ? { color: 'var(--adv)', fontWeight: 700 } : null}>{valor} %</span>
    </div>
  )
}

function Hallazgo({ h, sel, onClick }) {
  const Icono = h.tipo === 'adv' ? TriangleAlert : CircleAlert
  return (
    <button className={`hallazgo ${sel ? 'sel' : ''}`} onClick={onClick}>
      <Icono size={22} color="var(--adv)" style={{ flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <h4>{h.titulo}</h4>
        <p>{h.texto}</p>
        {h.cifras && (
          <div className="cifras num">
            {h.cifras.map(([k, v], i) => (
              <div key={k}><small>{k}</small><b style={i === 2 ? { color: 'var(--error)' } : null}>{v}</b></div>
            ))}
          </div>
        )}
        <div className="chips">
          <span className="chip"><Shield size={14} />Regla {h.regla}</span>
          <span className="chip">Versión {h.version}</span>
          <span className="chip"><File size={14} />Evidencia: {h.evidencia}</span>
        </div>
      </div>
    </button>
  )
}

const PASOS = ['Extrayendo datos', 'Consultando reglas', 'Validando', 'Preparando explicación']

function Procesando({ onTerminar }) {
  const [actual, setActual] = useState(0)
  useEffect(() => {
    if (actual >= PASOS.length) { const t = setTimeout(onTerminar, 600); return () => clearTimeout(t) }
    const t = setTimeout(() => setActual((a) => a + 1), 1300)
    return () => clearTimeout(t)
  }, [actual, onTerminar])
  return (
    <section className="tarjeta tarjeta-pad">
      <Estado valor="procesando" />
      <div className="pasos-proc">
        {PASOS.map((p, i) => {
          const estado = i < actual ? 'listo' : i === actual ? 'curso' : 'pend'
          return (
            <div className="paso-proc" key={p}>
              <span className={`c ${estado}`}>{estado === 'listo' && <Check size={16} />}</span>
              <span style={estado === 'pend' ? { color: 'var(--texto-2)' } : { fontWeight: estado === 'curso' ? 600 : 400 }}>{p}</span>
              <span className="et" style={{ color: estado === 'listo' ? 'var(--exito)' : estado === 'curso' ? 'var(--info)' : 'var(--texto-2)' }}>
                {estado === 'listo' ? 'Listo' : estado === 'curso' ? 'En curso' : 'Pendiente'}
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default function DetalleFactura({ caso, variante, setVariante, usuario, ir, toast }) {
  const [sel, setSel] = useState('total')
  const [pagina, setPagina] = useState(1)
  const [corrigiendo, setCorrigiendo] = useState(false)
  const [fecha, setFecha] = useState('12/08/2026')
  const [corregida, setCorregida] = useState(null)
  const [dialogo, setDialogo] = useState(false)
  const [estado, setEstado] = useState(caso.estado)
  const [eventos, setEventos] = useState(4)

  const resultado = { sinHallazgos: 'aceptado', faltaPolitica: 'humana', error: null, procesando: null }[variante] ?? caso.resultado
  const estadoVisible = variante === 'procesando' ? 'procesando' : variante === 'error' ? 'error' : estado
  const bloqueada = variante === 'procesando' || variante === 'error'

  function guardarCorreccion() {
    if (!corrigiendo) { setCorrigiendo(true); setSel('fecha'); return }
    setCorrigiendo(false)
    setCorregida({ antes: '12/03/2026', despues: fecha })
    setEventos((e) => e + 1)
    toast({ texto: 'Dato corregido y registrado en la bitácora' })
  }

  let columna
  if (variante === 'procesando') {
    columna = <Procesando onTerminar={() => setVariante('normal')} />
  } else if (variante === 'error') {
    columna = (
      <section className="tarjeta tarjeta-pad" style={{ display: 'grid', gap: 18 }}>
        <Banner tipo="error" icono={CircleAlert}>
          <b>No pudimos procesar este archivo.</b> El documento no se pudo leer. Puedes reintentar o subir una versión más legible.
        </Banner>
        <div style={{ display: 'flex', gap: 12 }}>
          <button className="btn btn-primario" onClick={() => setVariante('procesando')}><RotateCw size={18} />Reintentar</button>
          <button className="btn" onClick={() => ir('subir')}>Subir otro archivo</button>
        </div>
      </section>
    )
  } else if (variante === 'sinHallazgos') {
    columna = (
      <>
        <section className="tarjeta tarjeta-pad">
          <Banner tipo="info" icono={CircleCheck}>Sin hallazgos. Se evaluaron 12 reglas y todas se cumplen.</Banner>
        </section>
        <ResultadoSugerido resultado="aceptado">Todos los campos se leyeron con buena confianza y las reglas evaluadas se cumplen.</ResultadoSugerido>
      </>
    )
  } else if (variante === 'faltaPolitica') {
    columna = (
      <>
        <section className="tarjeta tarjeta-pad">
          <Banner tipo="adv" icono={TriangleAlert}>
            <b>No se encontró una regla aplicable a este caso.</b> El agente no puede sugerir un resultado sin una política vigente. Una persona debe revisarlo.
          </Banner>
        </section>
        <ResultadoSugerido resultado="humana" />
      </>
    )
  } else {
    columna = (
      <>
        <section className="tarjeta tarjeta-pad">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <h2>Datos extraídos</h2><span className="muted">Confianza de lectura</span>
          </div>
          {CAMPOS_FACTURA.map((c) => {
            const dudoso = c.conf < 80
            return (
              <div className="campo" key={c.id}>
                <div>
                  <div className="muted" style={{ color: 'var(--texto)' }}>{c.etiqueta}</div>
                  {dudoso && <span className="badge b-adv" style={{ marginTop: 6, fontSize: 13, padding: '2px 8px' }}><CircleAlert size={14} />Dudoso</span>}
                </div>
                {c.id === 'fecha' && corregida && !corrigiendo ? (
                  <div className="corregido">
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 17 }}>
                      <span className="antes num">{corregida.antes}</span><ArrowRight size={16} /><b className="num">{corregida.despues}</b>
                    </div>
                    <div className="quien">Corregido por {usuario.nombre} · 26 oct, 11:42</div>
                  </div>
                ) : (
                  <input
                    className={`num ${dudoso ? 'dudoso' : ''} ${corrigiendo && c.id === 'fecha' ? 'editable' : ''}`}
                    value={c.id === 'fecha' && corrigiendo ? fecha : c.valor}
                    readOnly={!(corrigiendo && c.id === 'fecha')}
                    autoFocus={corrigiendo && c.id === 'fecha'}
                    onChange={(e) => setFecha(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && guardarCorreccion()}
                    aria-label={c.etiqueta}
                  />
                )}
                <Confianza valor={c.conf} />
              </div>
            )
          })}
        </section>

        <section className="tarjeta tarjeta-pad">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 16 }}>
            <h2>Hallazgos <span className="muted" style={{ fontWeight: 400 }}>(2)</span></h2>
            <span className="muted" style={{ fontSize: 14 }}>Selecciona uno para verlo en el documento</span>
          </div>
          <div style={{ display: 'grid', gap: 16 }}>
            {HALLAZGOS_FACTURA.map((h) => (
              <Hallazgo key={h.id} h={h} sel={sel === h.id} onClick={() => { setSel(h.id); setPagina(1) }} />
            ))}
          </div>
        </section>

        <ResultadoSugerido resultado={resultado}>
          El total impreso es 400.00 mayor que la suma de subtotal e impuestos, y la fecha no se pudo leer con
          seguridad. El agente no puede determinar si la factura cumple las reglas sin que una persona lo verifique.
        </ResultadoSugerido>
      </>
    )
  }

  return (
    <main className="main con-barra">
      <Cabecera caso={caso} estado={estadoVisible} resultado={resultado} volver={() => ir('casos')} />
      <div className="det-grid">
        <Documento resaltar={variante === 'normal' ? sel : null} pagina={pagina} setPagina={setPagina} />
        <div className="col">{columna}</div>
      </div>
      <BarraAcciones
        eventos={eventos}
        deshabilitada={bloqueada}
        verBitacora={() => ir('bitacora')}
        corrigiendo={corrigiendo}
        onCorregir={guardarCorreccion}
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
          <p>Vas a confirmar el resultado sugerido <b>{RESULTADO_TXT[resultado] || 'sin resultado'}</b> para el caso {caso.id}. Quedará registrado en la bitácora.</p>
          <p style={{ fontSize: 15 }}>Esta confirmación no autoriza pagos ni operaciones.</p>
        </Dialogo>
      )}
    </main>
  )
}
